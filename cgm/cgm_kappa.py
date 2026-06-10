"""Linear-weighted Cohen's kappa for 1-5 rubric scores, with the explicit
degeneracy rule from the design spec: zero expected disagreement (both raters
constant at the same category) makes kappa undefined -> return None; the caller
treats None + 100% raw agreement as a gate PASS reported 'N/A (degenerate)'."""

CATEGORIES = (1, 2, 3, 4, 5)


def linear_weighted_kappa(a, b, categories=CATEGORIES):
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    span = k - 1

    obs_dis = sum(abs(idx[x] - idx[y]) / span for x, y in zip(a, b)) / n

    count_a = {c: 0 for c in categories}
    count_b = {c: 0 for c in categories}
    for x in a:
        count_a[x] += 1
    for y in b:
        count_b[y] += 1
    exp_dis = sum(
        (abs(idx[ca] - idx[cb]) / span) * count_a[ca] * count_b[cb]
        for ca in categories for cb in categories
    ) / (n * n)

    if exp_dis == 0:
        return None  # degenerate: both raters constant at the same category
    return 1 - obs_dis / exp_dis


def agreement_stats(a, b):
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    return {
        "raw_agreement": sum(x == y for x, y in zip(a, b)) / n,
        "adjacent_agreement": sum(abs(x - y) <= 1 for x, y in zip(a, b)) / n,
        "n": n,
    }
