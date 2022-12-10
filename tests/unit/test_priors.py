import numpy as np
import pytest

from smcpy.priors import ImproperUniform, InvWishart, ImproperCov

@pytest.mark.parametrize('sign', [-1, 1])
@pytest.mark.parametrize('x, expected', [(0, np.ones(1)), (1, np.ones(1)),
                                         (1e24, np.ones(1)),
                                         (np.ones(3), np.ones(3)),
                                         (np.ones((3, 1)), np.ones(3))])
def test_improper_uniform(sign, x, expected):
    prior = ImproperUniform()
    assert np.array_equal(prior.pdf(sign * x), expected)


@pytest.mark.parametrize('x', [np.ones((3, 2)), np.ones((2, 3))])
def test_improper_uniform_shape_error(x):
    prior = ImproperUniform()
    with pytest.raises(ValueError):
        prior.pdf(x)


@pytest.mark.parametrize('bounds, expected',
                         [((-5, 5), np.array([0, 1, 1, 1, 1, 1, 0])),
                          ((0, 5), np.array([0, 0, 0, 1, 1, 1, 0])),
                          ((0, None), np.array([0, 0, 0, 1, 1, 1, 1])),
                          ((None, None), np.array([1, 1, 1, 1, 1, 1, 1])),
                          ((None, 0), np.array([1, 1, 1, 1, 0, 0, 0])),
                          ((-10, None), np.array([0, 1, 1, 1, 1, 1, 1]))])
def test_improper_uniform_bounds(bounds, expected):
    x = np.array([-1000, -5, -2, 0, 2, 5, 1000])
    prior = ImproperUniform(*bounds)
    np.testing.assert_array_equal(prior.pdf(x), expected)


@pytest.mark.parametrize('n', [1, 2, 3, 4])
def test_invwishart_dim(n):
    iw = InvWishart(n, np.eye(n))
    assert iw.dim == (n + 1) * n / 2


@pytest.mark.parametrize('num_samples', [1, 5, 10])
def test_invwishart_sample(mocker, num_samples):
    cov_dim = 3
    cov_sample = np.array([[0, 1, 2], [1, 3, 4], [2, 4, 5]])
    expected_sample = np.tile(np.arange(6), (num_samples, 1))

    mock_invwis = mocker.Mock()
    mock_invwis.rvs.return_value = np.tile(cov_sample, (num_samples, 1, 1))
    mock_invwis_class = mocker.patch('smcpy.priors.invwishart',
                                     return_value=mock_invwis)

    iw = InvWishart(scale=np.eye(cov_dim), dof=cov_dim)

    np.testing.assert_array_equal(iw.rvs(num_samples), expected_sample)
    mock_invwis.rvs.assert_called_once_with(num_samples)
    iw_class_call = mock_invwis_class.call_args[0]
    assert iw_class_call[0] == cov_dim
    np.testing.assert_array_equal(iw_class_call[1], np.eye(cov_dim))


@pytest.mark.parametrize('num_samples', [1, 5, 10])
def test_invwishart_pdf(mocker, num_samples):
    cov_dim = 3
    samples = np.tile(np.arange(6), (num_samples, 1))
    cov_sample = np.array([[0, 1, 2], [1, 3, 4], [2, 4, 5]])
    expected_cov = np.tile(cov_sample, (num_samples, 1, 1))
    expected_cov = np.transpose(expected_cov, axes=(1, 2, 0))
    expected_prior_probs = np.ones(num_samples)

    mock_invwis = mocker.Mock()
    mock_invwis.pdf.return_value = np.ones(num_samples)
    mock_invwis_class = mocker.patch('smcpy.priors.invwishart',
                                     return_value=mock_invwis)

    iw = InvWishart(scale=np.eye(cov_dim), dof=cov_dim)

    np.testing.assert_array_equal(iw.pdf(samples), expected_prior_probs)
    np.testing.assert_array_equal(mock_invwis.pdf.call_args[0][0], expected_cov)


@pytest.mark.parametrize('num_samples', [1, 5])
def test_invwishart_zero_prob(mocker, num_samples):
    samples = np.tile(np.arange(6), (num_samples, 1))

    mock_invwis = mocker.Mock()
    mock_invwis.pdf.side_effect = np.linalg.LinAlgError
    mock_invwis_class = mocker.patch('smcpy.priors.invwishart',
                                     return_value=mock_invwis)

    iw = InvWishart(scale=np.eye(3), dof=3)

    np.testing.assert_array_equal(iw.pdf(samples), np.zeros((num_samples, 1)))


def test_impropcov_dim():
    p = ImproperCov(2)
    assert p.dim == 3


@pytest.mark.parametrize('cov', [np.ones((2, 4)), np.ones((10, 2, 1))])
def test_impropcov_bad_shape(cov):
    p = ImproperCov(2)
    with pytest.raises(ValueError):
        p.pdf(cov)


@pytest.mark.parametrize('posdefindex', [x for x in range(5)])
def test_impropcov_probability_nd(posdefindex):
    expected_prob = np.array([[0]] * 5)
    cov = np.array([[1., 2, 0]] * 5)

    cov[posdefindex, :] = np.array([1, 0.5, 1.5])
    expected_prob[posdefindex, 0] = 1

    p = ImproperCov(2)
    pdf = p.pdf(cov)

    np.testing.assert_array_equal(pdf, expected_prob)

@pytest.mark.parametrize('dof, scale, expdof, expscale',
                         [(None, None, 2, np.eye(2)),
                          (3, np.ones((2, 2)), 3, np.ones((2, 2)))])
def test_impropcov_rvs(mocker, dof, scale, expdof, expscale):
    mock_invwis = mocker.Mock()
    mock_invwis.rvs.return_value = np.arange(8).reshape(2, 2, 2)
    mock_invwis_class = mocker.patch('smcpy.priors.invwishart',
                                     return_value=mock_invwis)
    p = ImproperCov(2, dof, scale)
    samples = p.rvs(5)

    assert mock_invwis_class.call_args[0][0] == expdof
    np.testing.assert_array_equal(mock_invwis_class.call_args[0][1], expscale)
    mock_invwis.rvs.asser_called_once_with(5)
    np.testing.assert_array_equal(samples, np.array([[0, 1, 3], [4, 5, 7]]))

