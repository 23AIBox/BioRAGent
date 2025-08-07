import numpy as np
import pandas as pd
from statsmodels.stats.inter_rater import fleiss_kappa
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

def load_real_data(file_path):
    try:
        data = pd.read_csv(file_path, header=None, names=['Human', 'LLM'])
        print(f"Loaded data: {len(data)} rows")
        return data
    except Exception as e:
        print(f"Failed to load data: {e}")
        return None

def discretize_scores(score):
    if 0.0 <= score < 0.4:
        return 'Poor (0.0-0.4)'
    elif 0.4 <= score < 0.8:
        return 'Medium (0.4-0.8)'
    elif 0.8 <= score <= 1.0:
        return 'Good (0.8-1.0)'
    else:
        return 'Invalid'

score_data = load_real_data('./evaluation_llm/llm_human2.csv')
score_data.insert(0, 'SampleID', range(1, len(score_data)+1))
print("First 5 rows of score data:")
print(score_data)

discrete_data = score_data.copy()
for col in ['Human', 'LLM']:
    discrete_data[col] = discrete_data[col].apply(discretize_scores)

def build_fleiss_matrix(data, raters):
    categories = ['Poor (0.0-0.4)', 'Medium (0.4-0.8)', 'Good (0.8-1.0)']
    n_samples = len(data)
    n_categories = len(categories)
    fleiss_matrix = np.zeros((n_samples, n_categories))
    cat_to_idx = {cat: idx for idx, cat in enumerate(categories)}
    for i, row in data.iterrows():
        counts = {cat: 0 for cat in categories}
        for rater in raters:
            cat = row[rater]
            if cat in counts:
                counts[cat] += 1
        for cat, count in counts.items():
            fleiss_matrix[i, cat_to_idx[cat]] = count
    return fleiss_matrix

fleiss_input = build_fleiss_matrix(discrete_data, ['Human', 'LLM'])

def calc_p0(fleiss_matrix):
    n_samples, n_categories = fleiss_matrix.shape
    p0_list = []
    for i in range(n_samples):
        row = fleiss_matrix[i]
        n_raters = row.sum()
        agree = np.sum(row * (row - 1))
        total = n_raters * (n_raters - 1)
        p0 = agree / total if total > 0 else np.nan
        p0_list.append(p0)
    return np.nanmean(p0_list)

p0 = calc_p0(fleiss_input)
print(f"P₀ (Observed agreement rate): {p0:.4f}")

try:
    kappa = fleiss_kappa(fleiss_input)
    print(f"\nFleiss' κ (Human + LLM): {kappa:.4f}")
except Exception as e:
    print(f"Error calculating Fleiss' κ: {e}")
    kappa = np.nan

def bootstrap_kappa(matrix, n_iter=1000):
    kappas = []
    n = len(matrix)
    for _ in range(n_iter):
        sample_idx = np.random.choice(n, n, replace=True)
        sample_matrix = matrix[sample_idx]
        try:
            k = fleiss_kappa(sample_matrix)
            kappas.append(k)
        except:
            continue
    if kappas:
        return np.quantile(kappas, 0.025), np.quantile(kappas, 0.975)
    else:
        return (np.nan, np.nan)

lower_ci, upper_ci = bootstrap_kappa(fleiss_input)
print(f"95% confidence interval: [{lower_ci:.4f}, {upper_ci:.4f}]")

def category_agreement(matrix, categories):
    agreement = {}
    total_ratings = matrix.sum()
    for i, cat in enumerate(categories):
        cat_count = matrix[:, i].sum()
        agreement[cat] = cat_count / total_ratings
    return agreement

categories = ['Poor (0.0-0.4)', 'Medium (0.4-0.8)', 'Good (0.8-1.0)']
agreement = category_agreement(fleiss_input, categories)
print("\nCategory agreement proportions:")
for cat, prop in agreement.items():
    print(f"{cat}: {prop:.4f}")

print("\n" + "="*80)
print("Human and LLM Evaluation Consistency Analysis Report (Three-class)".center(80))
print("="*80)
print(f"Number of samples: {len(score_data)}")
print(f"Raters: 1 human + 1 LLM")
print(f"Evaluation standard: 3-class (Poor, Medium, Good)")
print("-"*80)
if not np.isnan(kappa):
    print(f"Fleiss' κ (Human + LLM): {kappa:.4f} [95%CI: {lower_ci:.4f}-{upper_ci:.4f}]")
else:
    print("Fleiss' κ calculation failed")
print("-"*80)
print("Landis & Koch interpretation standard:")
print(" > 0.81: Almost perfect agreement")
print(" 0.61-0.80: Substantial agreement")
print(" 0.41-0.60: Moderate agreement")
print(" 0.21-0.40: Fair agreement")
print(" < 0.20: Slight or no agreement")
print("-"*80)
print("Category agreement proportions:")
for cat, prop in agreement.items():
    print(f" - {cat}: {prop*100:.1f}%")
print("="*80)

full_results = pd.concat([score_data, discrete_data.add_prefix('Discrete_')], axis=1)
full_results.to_csv('human_llm_evaluation_results_class.csv', index=False)
