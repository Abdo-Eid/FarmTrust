#!/usr/bin/env python3
"""
Hidden Markov Model for crop phenology from an NDVI time series.
================================================================

THE IDEA
--------
On any date the field is in ONE of four hidden phases:
    LOW  (bare / dormant)   RISING (green-up)   HIGH (peak)   DECLINING (senescence)
We never see the phase directly -- we only see NDVI. The HMM infers the phase at
every date, and the contiguous RISING->HIGH->DECLINING runs are the crop cycles.

Every HMM has just THREE ingredients, all LEARNED from the data:
    1. start probabilities   pi[k]    -- how likely we begin in state k
    2. transition matrix     A[j,k]   -- probability of moving from state j to state k
    3. emission model    (mean,var)   -- the NDVI each state typically produces (a Gaussian)

TWO algorithms:
    * Baum-Welch (EM)  -> LEARNS pi, A, and the emissions from the NDVI curve
    * Viterbi          -> finds the single most likely phase sequence

WHY TWO NUMBERS PER DATE
------------------------
We feed the model [NDVI value, NDVI slope]. RISING and DECLINING sit at the SAME
NDVI level (~0.5) and differ only in direction, so without the slope the model
cannot tell green-up from senescence.
"""
import numpy as np


# 1) EMISSION: how well does an observation fit a state? (log of a diagonal Gaussian)
def log_gaussian(X, mean, var):
    d = X - mean
    return -0.5 * np.sum(d * d / var + np.log(2 * np.pi * var), axis=1)

def logsumexp(a, axis):                       # numerically safe log(sum(exp(a)))
    m = np.max(a, axis=axis, keepdims=True)
    return m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))


# 2) TRAIN with Baum-Welch (Expectation-Maximisation)
def fit_hmm(X, init_means, n_iter=30):
    """X: (T,2) [value, slope] per date.  init_means: (4,2) starting guess per state."""
    T, D = X.shape
    K = len(init_means)
    means = init_means.astype(float).copy()
    var   = np.tile(X.var(0) + 1e-2, (K, 1))                      # how spread each state is
    A     = np.full((K, K), 0.04); np.fill_diagonal(A, 1 - 0.04 * (K - 1))  # start "sticky"
    pi    = np.full(K, 1.0 / K)

    for _ in range(n_iter):
        # ---- E-step: given current parameters, how likely is each state on each date? ----
        logB = np.stack([log_gaussian(X, means[k], var[k]) for k in range(K)], axis=1)  # (T,K)
        logA, logpi = np.log(A + 1e-12), np.log(pi + 1e-12)

        # forward: prob of the data UP TO t and being in state k now
        la = np.zeros((T, K)); la[0] = logpi + logB[0]
        for t in range(1, T):
            la[t] = logB[t] + logsumexp(la[t - 1][:, None] + logA, axis=0).ravel()
        # backward: prob of the data AFTER t, given state k now
        lb = np.zeros((T, K))
        for t in range(T - 2, -1, -1):
            lb[t] = logsumexp(logA + logB[t + 1][None, :] + lb[t + 1][None, :], axis=1).ravel()

        gamma = np.exp((la + lb) - logsumexp(la + lb, axis=1))     # P(state k at t | all data)
        xi = np.zeros((K, K))                                      # expected j->k transitions
        for t in range(T - 1):
            m = la[t][:, None] + logA + logB[t + 1][None, :] + lb[t + 1][None, :]
            xi += np.exp(m - logsumexp(m.reshape(1, -1), axis=1))

        # ---- M-step: re-estimate the three ingredients from those soft assignments ----
        pi = gamma[0] / gamma[0].sum()
        A  = xi / (gamma[:-1].sum(0)[:, None] + 1e-12); A /= A.sum(1, keepdims=True)
        for k in range(K):
            w = gamma[:, k]; sw = w.sum() + 1e-12
            means[k] = (w[:, None] * X).sum(0) / sw
            var[k]   = (w[:, None] * (X - means[k]) ** 2).sum(0) / sw + 1e-3
    return means, var, A, pi


# 3) DECODE the single most likely phase sequence (Viterbi = "best path")
def viterbi(X, means, var, A, pi):
    T, K = len(X), len(means)
    logB = np.stack([log_gaussian(X, means[k], var[k]) for k in range(K)], axis=1)
    logA, logpi = np.log(A + 1e-12), np.log(pi + 1e-12)
    delta = np.zeros((T, K)); back = np.zeros((T, K), int)
    delta[0] = logpi + logB[0]
    for t in range(1, T):                       # best score to arrive at each state
        m = delta[t - 1][:, None] + logA
        back[t] = m.argmax(0); delta[t] = logB[t] + m.max(0)
    path = np.zeros(T, int); path[-1] = delta[-1].argmax()
    for t in range(T - 2, -1, -1):              # follow the back-pointers
        path[t] = back[t + 1][path[t + 1]]
    return path


# 4) END-TO-END on an NDVI series
def phases_from_ndvi(z):
    """z: 1-D smoothed daily NDVI -> array of phase labels per day."""
    X = np.column_stack([z, np.gradient(z)])            # [value, slope]
    X = (X - X.mean(0)) / X.std(0)                      # standardise so both matter equally
    init = np.array([[-1.2, 0.0],    # LOW       : low value,  flat
                     [ 0.0, 1.6],    # RISING    : mid value,  going up
                     [ 1.3, 0.0],    # HIGH      : high value, flat
                     [ 0.0,-1.6]])   # DECLINING : mid value,  going down
    means, var, A, pi = fit_hmm(X, init)
    states = viterbi(X, means, var, A, pi)
    # label the 4 learned states by their mean [value, slope]
    order = np.argsort(means[:, 0]); LOW, HIGH = order[0], order[3]
    mids = order[1:3]
    RISING = mids[means[mids, 1].argmax()]; DECL = mids[means[mids, 1].argmin()]
    name = {LOW: "LOW", RISING: "RISING", HIGH: "HIGH", DECL: "DECLINING"}
    return np.array([name[s] for s in states]), means, A


# ---- tiny self-contained demo on a synthetic two-cycle NDVI curve ----
if __name__ == "__main__":
    t = np.arange(730)
    # two bell-shaped crop cycles + a bare-soil floor + noise
    z = 0.18 + 0.0*t
    for c in (140, 470):
        z = z + 0.62 * np.exp(-((t - c) ** 2) / (2 * 45 ** 2))
    rng = np.random.default_rng(0); z = z + rng.normal(0, 0.01, t.size)
    labels, means, A = phases_from_ndvi(z)
    # print the phase the model is in, sampled every ~6 weeks
    for i in range(0, len(t), 45):
        print(f"day {t[i]:3d}  NDVI {z[i]:.2f}  ->  {labels[i]}")
    print("\nlearned state means [value, slope] (standardised):\n", np.round(means, 2))
