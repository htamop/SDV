from unittest.mock import patch

import pandas as pd
import pytest
from copulas.multivariate.gaussian import GaussianMultivariate

from sdv.constraints import Unique, UniqueCombinations
from sdv.constraints.tabular import GreaterThan
from sdv.demo import load_tabular_demo
from sdv.sampling import Condition
from sdv.tabular.copulagan import CopulaGAN
from sdv.tabular.copulas import GaussianCopula
from sdv.tabular.ctgan import CTGAN, TVAE

MODELS = [
    pytest.param(CTGAN(epochs=1), id='CTGAN'),
    pytest.param(TVAE(epochs=1), id='TVAE'),
    pytest.param(GaussianCopula(), id='GaussianCopula'),
    pytest.param(CopulaGAN(epochs=1), id='CopulaGAN'),
]


def _isinstance_side_effect(*args, **kwargs):
    if isinstance(args[0], GaussianMultivariate):
        return True
    else:
        return isinstance(args[0], args[1])


def test___init___copies_metadata():
    """Test the ``__init__`` method.

    This test assures that the metadata provided to the model is copied,
    so that any modifications don't change the input.

    Setup:
        - Initialize two models with the same metadata and data.

    Expected behavior:
        - The metadata for each model and the provided metadata should all be different.
    """
    # Setup
    metadata, data = load_tabular_demo('student_placements', metadata=True)

    # Run
    model = GaussianCopula(table_metadata=metadata,
                           categorical_transformer='label_encoding',
                           default_distribution='gamma')
    model.fit(data)
    model2 = GaussianCopula(table_metadata=metadata,
                            categorical_transformer='label_encoding',
                            default_distribution='beta')
    model2.fit(data)

    # Assert
    assert model._metadata != metadata
    assert model._metadata != model2._metadata
    assert model2._metadata != metadata
    gamma = 'copulas.univariate.gamma.GammaUnivariate'
    beta = 'copulas.univariate.beta.BetaUnivariate'
    assert all(distribution == gamma for distribution in model.get_distributions().values())
    assert all(distribution == beta for distribution in model2.get_distributions().values())


@pytest.mark.parametrize('model', MODELS)
def test_conditional_sampling_graceful_reject_sampling_True_dict(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)
    conditions = [Condition({
        'column1': 28,
        'column2': 37,
        'column3': 93
    })]

    with pytest.raises(ValueError):
        model.sample_conditions(conditions=conditions)


@pytest.mark.parametrize('model', MODELS)
def test_conditional_sampling_graceful_reject_sampling_True_dataframe(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)
    conditions = pd.DataFrame({
        'column1': [28],
        'column2': [37],
        'column3': [93]
    })

    with pytest.raises(ValueError):
        model.sample_remaining_columns(conditions)


def test_fit_with_unique_constraint_on_data_with_only_index_column():
    """Test that the ``fit`` method runs without error when metadata specifies unique constraint,
    ``fit`` is called on data containing a column named index.

    The ``fit`` method is expected to fit the model to data,
    taking into account the metadata and the ``Unique`` constraint.

    Setup:
    - The model is passed the unique constraint and
    the primary key column.

    Input:
    - Data, Unique constraint

    Github Issue:
    - Tests that https://github.com/sdv-dev/SDV/issues/616 does not occur
    """
    # Setup
    test_df = pd.DataFrame({
        "key": [
            1,
            2,
            3,
            4,
            5,
        ],
        "index": [
            "A",
            "B",
            "C",
            "D",
            "E",
        ]
    })
    unique = Unique(columns=["index"])
    model = GaussianCopula(primary_key="key", constraints=[unique])

    # Run
    model.fit(test_df)
    samples = model.sample(2)

    # Assert
    assert len(samples) == 2
    assert samples["index"].is_unique


def test_fit_with_unique_constraint_on_data_which_has_index_column():
    """Test that the ``fit`` method runs without error when metadata specifies unique constraint,
    ``fit`` is called on data containing a column named index and other columns.

    The ``fit`` method is expected to fit the model to data,
    taking into account the metadata and the ``Unique`` constraint.

    Setup:
    - The model is passed the unique constraint and
    the primary key column.
    - The unique constraint is set on the ``test_column``

    Input:
    - Data, Unique constraint

    Github Issue:
    - Tests that https://github.com/sdv-dev/SDV/issues/616 does not occur
    """
    # Setup
    test_df = pd.DataFrame({
        "key": [
            1,
            2,
            3,
            4,
            5,
        ],
        "index": [
            "A",
            "B",
            "C",
            "D",
            "E",
        ],
        "test_column": [
            "A1",
            "B2",
            "C3",
            "D4",
            "E5",
        ]
    })
    unique = Unique(columns=["test_column"])
    model = GaussianCopula(primary_key="key", constraints=[unique])

    # Run
    model.fit(test_df)
    samples = model.sample(2)

    # Assert
    assert len(samples) == 2
    assert samples["test_column"].is_unique


def test_fit_with_unique_constraint_on_data_subset():
    """Test that the ``fit`` method runs without error when metadata specifies unique constraint,
    ``fit`` is called on a subset of the original data.

    The ``fit`` method is expected to fit the model to the subset of data,
    taking into account the metadata and the ``Unique`` constraint.

    Setup:
    - The model is passed a ``Unique`` constraint and is
    matched to a subset of the specified data.
    Subdividing the data results in missing indexes in the subset contained in the original data.

    Input:
    - Subset of data, unique constraint

    Github Issue:
    - Tests that https://github.com/sdv-dev/SDV/issues/610 does not occur
    """
    # Setup
    test_df = pd.DataFrame({
        "key": [
            1,
            2,
            3,
            4,
            5,
        ],
        "test_column": [
            "A",
            "B",
            "C",
            "D",
            "E",
        ]
    })
    unique = Unique(
        columns=["test_column"]
    )

    test_df = test_df.iloc[[1, 3, 4]]
    model = GaussianCopula(primary_key="key", constraints=[unique])

    # Run
    model.fit(test_df)
    samples = model.sample(2)

    # Assert
    assert len(samples) == 2
    assert samples["test_column"].is_unique


@patch('sdv.tabular.base.isinstance')
@patch('sdv.tabular.copulas.copulas.multivariate.GaussianMultivariate',
       spec_set=GaussianMultivariate)
def test_conditional_sampling_constraint_uses_reject_sampling(gm_mock, isinstance_mock):
    """Test that the ``sample`` method handles constraints with conditions.

    The ``sample`` method is expected to properly apply constraint
    transformations by dropping columns that cannot be conditonally sampled
    on due to them being part of a constraint if ``fit_columns_model``
    is False.

    Setup:
    - The model is being passed a ``UniqueCombination`` constraint and then
    asked to sample with two conditions, one of which the constraint depends on.
    The constraint is expected to skip its transformations since only some of
    the columns are provided by the conditions and the model will use reject
    sampling to meet the constraint instead.

    Input:
    - Conditions
    Side Effects:
    - Correct columns to condition on are passed to underlying sample method
    """
    # Setup
    isinstance_mock.side_effect = _isinstance_side_effect
    constraint = UniqueCombinations(
        columns=['city', 'state'],
        handling_strategy='transform',
        fit_columns_model=False
    )
    data = pd.DataFrame({
        'city': ['LA', 'SF', 'CHI', 'LA', 'LA'],
        'state': ['CA', 'CA', 'IL', 'CA', 'CA'],
        'age': [27, 28, 26, 21, 30]
    })
    model = GaussianCopula(constraints=[constraint], categorical_transformer='label_encoding')
    sampled_numeric_data = [pd.DataFrame({
        'city#state.value': [0, 1, 2, 0, 0],
        'age.value': [30, 30, 30, 30, 30]
    }), pd.DataFrame({
        'city#state.value': [1],
        'age.value': [30]
    })]
    gm_mock.return_value.sample.side_effect = sampled_numeric_data
    model.fit(data)

    # Run
    conditions = [Condition({'age': 30, 'state': 'CA'}, num_rows=5)]
    sampled_data = model.sample_conditions(conditions=conditions)

    # Assert
    expected_transformed_conditions = {'age.value': 30}
    expected_data = pd.DataFrame({
        'city': ['LA', 'SF', 'LA', 'LA', 'SF'],
        'state': ['CA', 'CA', 'CA', 'CA', 'CA'],
        'age': [30, 30, 30, 30, 30]
    })
    sample_calls = model._model.sample.mock_calls
    assert len(sample_calls) == 2
    model._model.sample.assert_any_call(50, conditions=expected_transformed_conditions)
    pd.testing.assert_frame_equal(sampled_data, expected_data)


@patch('sdv.tabular.base.isinstance')
@patch('sdv.tabular.copulas.copulas.multivariate.GaussianMultivariate',
       spec_set=GaussianMultivariate)
def test_conditional_sampling_constraint_uses_columns_model(gm_mock, isinstance_mock):
    """Test that the ``sample`` method handles constraints with conditions.

    The ``sample`` method is expected to properly apply constraint
    transformations by sampling the missing columns for the constraint
    if ``fit_columns_model`` is True.

    Setup:
    - The model is being passed a ``UniqueCombination`` constraint and then
    asked to sample with two conditions, one of which the constraint depends on.
    The constraint will sample the columns it needs that are not present in
    the conditions and will then use constraint transformations to meet the
    requirements.

    Input:
    - Conditions
    Side Effects:
    - Correct columns to condition on are passed to underlying sample method
    """
    # Setup
    isinstance_mock.side_effect = _isinstance_side_effect
    constraint = UniqueCombinations(
        columns=['city', 'state'],
        handling_strategy='transform',
        fit_columns_model=True,
    )
    data = pd.DataFrame({
        'city': ['LA', 'SF', 'CHI', 'LA', 'LA'],
        'state': ['CA', 'CA', 'IL', 'CA', 'CA'],
        'age': [27, 28, 26, 21, 30]
    })
    model = GaussianCopula(constraints=[constraint], categorical_transformer='label_encoding')
    sampled_numeric_data = [pd.DataFrame({
        'city#state.value': [2],
        'age.value': [30]
    }), pd.DataFrame({
        'city#state.value': [1, 1, 0, 0, 0],
        'age.value': [30, 30, 30, 30, 30]
    }), pd.DataFrame({
        'city#state.value': [0, 0, 1, 1, 1],
        'age.value': [30, 30, 30, 30, 30]})
    ]
    gm_mock.return_value.sample.side_effect = sampled_numeric_data
    model.fit(data)

    # Run
    conditions = [Condition({'age': 30, 'state': 'CA'}, num_rows=5)]
    sampled_data = model.sample_conditions(conditions=conditions)

    # Assert
    expected_states = pd.Series(['CA', 'CA', 'CA', 'CA', 'CA'], name='state')
    expected_ages = pd.Series([30, 30, 30, 30, 30], name='age')
    sample_calls = model._model.sample.mock_calls
    assert len(sample_calls) >= 2 and len(sample_calls) <= 3
    assert all(c[2]['conditions']['age.value'] == 30 for c in sample_calls)
    assert all('city#state.value' in c[2]['conditions'] for c in sample_calls)
    pd.testing.assert_series_equal(sampled_data['age'], expected_ages)
    pd.testing.assert_series_equal(sampled_data['state'], expected_states)
    assert all(c in ('SF', 'LA') for c in sampled_data['city'])


@patch('sdv.constraints.base.GaussianMultivariate',
       spec_set=GaussianMultivariate)
def test_conditional_sampling_constraint_uses_columns_model_reject_sampling(column_model_mock):
    """Test that the ``sample`` method handles constraints with conditions.

    The ``sample`` method is expected to properly apply constraint
    transformations by sampling the missing columns for the constraint
    if ``fit_columns_model`` is True. All values sampled by the column
    model should be valid because reject sampling is used on any that aren't.

    Setup:
    - The model is being passed a ``GreaterThan`` constraint and then
    asked to sample with one condition. One of the constraint columns is
    the conditioned column. The ``GaussianMultivariate`` class is mocked
    so that the constraint's ``_column_model`` returns some invalid rows
    in order to test that the reject sampling is used.

    Input:
    - Conditions
    Side Effects:
    - Correct columns to condition on are passed to underlying sample method
    """
    # Setup
    constraint = GreaterThan(
        low='age_joined',
        high='age',
        handling_strategy='transform',
        fit_columns_model=True,
        drop='high'
    )
    data = pd.DataFrame({
        'age_joined': [22.0, 21.0, 15.0, 18.0, 29.0],
        'age': [27.0, 28.0, 26.0, 21.0, 30.0],
        'experience_years': [6.0, 7.0, 11.0, 3.0, 7.0],
    })
    model = GaussianCopula(constraints=[constraint])
    sampled_conditions = [
        pd.DataFrame({
            'age_joined.value': [26.0, 18.0, 31.0, 29.0, 32.0],
            'age.value': [30.0, 30.0, 30.0, 30.0, 30.0]
        }),
        pd.DataFrame({
            'age_joined.value': [28.0, 33.0, 31.0],
            'age.value': [30.0, 30.0, 30.0]
        }),
        pd.DataFrame({
            'age_joined.value': [27.0],
            'age.value': [30.0]
        })
    ]

    column_model_mock.return_value.sample.side_effect = sampled_conditions
    model.fit(data)

    # Run
    conditions = [Condition({'age': 30.0}, num_rows=5)]
    sampled_data = model.sample_conditions(conditions=conditions)

    # Assert
    assert len(column_model_mock.return_value.sample.mock_calls) == 3

    expected_result = pd.DataFrame({
        'age_joined': [26.0, 18.0, 29.0, 28.0, 27.0],
        'age': [30.0, 30.0, 30.0, 30.0, 30.0]
    })
    pd.testing.assert_frame_equal(
        sampled_data[['age_joined', 'age']],
        expected_result[['age_joined', 'age']],
    )


@pytest.mark.parametrize('model', MODELS)
def test_sampling_with_randomize_samples_True(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)

    sampled1 = model.sample(10, randomize_samples=True)
    sampled2 = model.sample(10, randomize_samples=True)

    assert not sampled1.equals(sampled2)


@pytest.mark.parametrize('model', MODELS)
def test_sampling_with_randomize_samples_False(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)

    sampled1 = model.sample(10, randomize_samples=False)
    sampled2 = model.sample(10, randomize_samples=False)

    pd.testing.assert_frame_equal(sampled1, sampled2)


@pytest.mark.parametrize('model', MODELS)
def test_sampling_with_randomize_samples_alternating(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)

    sampled_fixed1 = model.sample(10, randomize_samples=False)
    sampled_random1 = model.sample(10, randomize_samples=True)
    sampled_fixed2 = model.sample(10, randomize_samples=False)
    sampled_random2 = model.sample(10, randomize_samples=True)

    pd.testing.assert_frame_equal(sampled_fixed1, sampled_fixed2)
    assert not sampled_random1.equals(sampled_fixed1)
    assert not sampled_random1.equals(sampled_random2)
    assert not sampled_random2.equals(sampled_fixed1)
