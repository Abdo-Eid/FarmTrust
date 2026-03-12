---
keep_as_user: true
title: FarmTrust satellite land assessment legacy capture
migrated_from: docs/inbox.md
---

2026-01-25 - FarmTrust: Satellite-based land evaluation for agri-finance

# FarmTrust Project Overview - Satellite-Based Agricultural Land Assessment for Banks and Agri-Finance

## What are we doing?

We process satellite imagery of agricultural land to:

- assess land condition and agricultural activity
- produce signals/indicators that banks can understand
- make financing decisions easier for banks and agri-finance companies through an objective assessment of land condition and agricultural behavior over time (especially historical)

**Important:** We are working "Satellite-only" - no ground sensors and no field visits as a core requirement.

> We are not required to output the best quality or results, but to prove that it is possible and that we are on the right path.

## The problem we are solving

When a bank funds a farmer, it has a "transparency" problem:

- it cannot see the land over time
- it often relies on talk, paperwork, or a one-time field visit
- it does not know:
    - is the land actually active or not?
    - is it farmed regularly or intermittently?
    - are there chronic issues (salinity/waterlogging/drainage)?
    - is performance improving or declining over the years?

So we provide a "Visibility" layer that makes the decision easier and closer to reality.

## What does it mean to "assess land"? (full vision + POC/MVP part)

### Full vision

We want to turn satellite imagery into something like a "land profile" that the bank can understand quickly, and that answers questions such as:

- is the land **active or not**? and how much is it being cultivated?
- is performance **improving or deteriorating** over time?
- are there **chronic operational problems**? (water/salinity/poor drainage/...)

Also, in phases (not necessarily in the first version):

- add **broad crop classifications** instead of exact names (winter/summer/perennial + water-demand class + season length) from satellite time series, because that is more useful for banks and easier in the Egypt context
- produce **"production potential" assessment** as a class (low/medium/high) instead of a binding production number - this needs time and accumulated data/validation
- do **post-financing monitoring** and alerts for the bank if a clear risk appears:
    - sudden activity stop
    - a season disrupted in an abnormal way
    - increasing signs of waterlogging/salinity
    - encroachment/land-use change
- develop stronger models that help us do **labeling** and gradually build Egyptian datasets (like crop mapping/segmentation) and publish part of them as research/community outputs when appropriate

```
# Random notes and ideas
**Academic note (for the project and graduation):**

- Although we will start with broad classes, we are also thinking about **higher detail**: attempting **crop type identification** instead of a general class (this helps research and helps us launch our own dataset). We could train a large slow model (teacher) on many available datasets and remove crops that are not common in Egypt, then build high-quality data on Egyptian lands and train a smaller model specifically for Egypt, and maybe even design our own architecture.
    - **Domain adaptation:** adapting models trained on global agricultural data (satellite imagery and non-Egyptian crops) to the Egyptian context by reducing the gap between spectral/temporal distributions of global data and Egyptian agricultural lands, even when local ground truth is absent or scarce.
    - **Weak labeling:** using indirect or approximate labels (like agricultural calendars "if the period is winter, it is likely winter crops", temporal features of vegetation curves, or low-resolution global maps or clustering "land similar to land" and labeling them with broad tags) as a substitute for full ground truth, to enable training crop classifiers or yield estimators in a data-scarce environment.
- Also study **more detailed productivity modeling**: instead of only "low/medium/high", produce a **semi-quantitative estimate** (Relative Yield Index or ranking within the region) as an intermediate stage before any actual yield number. This reduces risk and preserves research value even without strong local ground truth.
```

### POC/MVP part (what we can deliver quickly and confidently - decision support only)

- **Clear land status** (active / intermittent / inactive) backed by time-based indicators from satellite imagery
- **Last two-year trend** (improving / stable / declining) based on seasonal performance indicators and local neighbor comparison
- **Last available season performance** (stable vs. shock/abrupt interruption within the season)
- **Simple and clear risk flags**: waterlogging/poor drainage, **salinity likelihood**, encroachment/land-use change
- **Short report "reason + recommendation"** instead of technical language, suitable for funding decisions and follow-up
- optionally a **Confidence level** for each result (High/Medium/Low) depending on observation quality (clouds/number of scenes/season clarity)

**All of the above is built on clear Key Statistics, such as:**

- **Cropping intensity**: number of seasons per year + duration of fallow periods
- **Season timing**: season start/end and how it changes over two years
- **Vegetation strength**: Peak NDVI/EVI + AUC (total seasonal activity)
- **Within-season stability**: number of shocks and sudden drops
- **Spatial uniformity**: performance uniformity within the plot (persistent weak patches or not)
- **Water indicators**: moisture regularity (NDMI) + waterlogging frequency (NDWI)
- **Neighbor comparison**: plot ranking compared to neighbors in the same period

This helps the reader understand: "You are making a judgment... but the judgment is based on clear numbers."

This is more than enough for a bank to make a practical financing decision with confidence, because we provide **temporal visibility + explanation + risk signals** instead of relying on a single snapshot or general statements.

## Expected challenges (Reality Check)

- **Small holdings + mixed crops (Mixed pixels):** small plots and mixing within the same plot make the pixel signature "mixed", so classifying a _single confirmed crop_ becomes difficult, especially with narrow strips and intercropping.
- **Boundary accuracy:** any boundary error brings in neighbors into the calculation, which distorts indicators and ruins conclusions - especially when plots are small and boundaries are many.
    ```
    # Random notes and ideas
    I think we need a model that can draw boundaries
    and a model that can determine if the land is cultivated or not via segmentation, but distinguish non-cultivated areas that could be buildings or roads or fallow. This model will help in more than one place across the project, I think.
    ```
- **Time series gaps due to clouds/fog/aerosols/shadows:** creates artificial jumps in NDVI/EVI and breaks the seasonal curve, which can appear as "decline" or "improvement" when it is just poor observation quality.
    ```
    # Random notes and ideas
    There are probably methods to handle this, and if we avoid imitation and find a new clean approach, that is in our favor.
    * **Classical gap-filling:** reconstruct a smooth seasonal curve and fill missing points so trends/phases stay stable (mainly removes cloud/shadow spikes).
    * **Multi-source fusion:** when optical is missing, use an alternate signal to keep continuity, then align/normalize it back to the same seasonal timeline.
    * **Spatial borrowing / robust aggregation:** estimate plot value from only "good" pixels or nearby similar plots, lowering missingness without inventing sharp jumps.
    * **Model-based imputation:** learn typical temporal dynamics and predict missing segments with uncertainty, producing a filled series + confidence.
    * **Gap-tolerant features:** avoid filling; detect phases/changes using robust features that require persistence across observations, so gaps don't trigger false alarms.

    **General workflow:** quality mask -> build plot-level time series -> smooth/de-spike -> gap-fill (or skip) -> compute phase/change features -> output signal + confidence.

    **Rule of thumb:**
    Small holes -> classical smoothing + light interpolation works well;
    long cloudy periods -> multi-source fusion or model-based imputation is safer;
    for bank alerts -> be conservative and always propagate a confidence score to avoid false alarms.
    ```
- **Strong environmental differences within Egypt (Delta/Valley/Reclaimed):** the same agricultural behavior can appear with different spectral/temporal signatures depending on environment, soil, and water, so general rules fail if applied literally across all governorates.
- **Agricultural calendars are not fixed + continuous planting:** planting and harvest dates shift, and there can be more than one cycle per year, so interpretation based on a "fixed calendar" is misleading in many cases.
- **Irregular irrigation and water issues:** irrigation can spike indicators then drop, showing sharp changes that do not reflect true seasonal performance (temporary improvement / false decline).
- **Confusion between "plant health" and "land activity":** signals may show weak plant health while the land is "active", or the opposite; the bank cares more about activity, continuity, and risk than precise agronomic diagnosis.
- **Lack/scarcity of local ground truth at plot level:** lack of reliable labels reduces crop classification quality (if attempted) and increases uncertainty for detailed conclusions.
- **False alarms and operational trust:** wrong alerts or unstable decisions break credit-team trust quickly, especially if outputs are unstable or change without clear reason.
- **Interpretability for the bank:** the bank will not use complex maps or heavy agronomic terminology; if outputs are not direct and clear, operational resistance arises even if the model is "good".
- **Local comparison with neighbors can hide collective risk:** if the whole region is affected (heat wave/water shortage/general irrigation issue), neighbor comparison alone may show the plot as "normal" even though there is a real risk for everyone.
- **Performance and scaling:** running time series and analytics for thousands of plots creates compute and storage pressure (especially with periodic updates and local comparisons), which is a challenge if we want to scale quickly.

> Currently all challenges are at the same level. For the bank/evaluator, it is better to start with the highest risk to trust.

## Constraints and fit for Egypt

Egypt: small holdings + continuous farming + mixed crops + limited local data.

Therefore, the best approach is: **temporal analysis + local comparison + interpretation + confidence score**.

- **Sentinel-2 (10m)** is suitable for most holdings
- primary reliance is on **time**, not fine spatial details
- local comparison reduces noise and gives a more reliable judgment

**Summary:** free-resolution + smart temporal analysis = real value even with small plots.

> <branch> Is there another approach? I do not know.
> member comment -> In data-scarce agricultural systems like Egypt, the most robust and deployable approach is not fine-grained crop or yield prediction, but temporal behavioral assessment of land activity using satellite time-series, supported by local comparison, interpretable indicators, and explicit uncertainty.

## Land and soil quality (Satellite proxies, not lab analysis)

### Important fact

**"Direct" soil quality is not measured from satellites like lab soil samples.**

But we can extract strong **proxy indicators** that serve financing decisions, such as:

- operational fertility: does the land consistently produce strong vegetation?
- water stress: drought / weak irrigation
- waterlogging / poor drainage
- salinity (as a risk indicator)
- within-plot heterogeneity (strong patches and weak patches)
- improvement/decline trends over time

**Why is this useful for the bank?**

Because the bank cares about: "Does the land deliver stable performance? Are there operational risks?" more than a chemical soil definition.

## Two-year analysis (Behavior + Trend)

Two years back (24 months) is very suitable to derive "behavior" and "trend" rather than a single snapshot.

1. **Cropping Intensity:** number of cycles per year (1/2/3), length of fallow periods between seasons, **example for the bank:** "the land was active in 5 of the last 8 seasons"
2. **Stability in season timing (Phenology):** green-up start and senescence end; are timings stable or unusually delayed/advanced? **Reason:** repeated delays can indicate management/irrigation/readiness/financing issues.

    > Even if we cannot answer these questions ourselves, if we can notice them we can include them, and they can ask about them. They might even provide them in the application and we can collect data.

3. **Performance trend (Productivity proxy):** trend of **Peak NDVI** or **AUC** across seasons; **Rule:** "continuous decline" = warning sign.
4. **Anomaly vs neighbors:** compare the land to nearby plots in the same area and same period; **Reason:** weather affects everyone, so local comparison answers: "Is this plot weaker than normal? Or is the whole season weak?"
5. **Stability Index (stable or volatile):** high variability season-to-season -> higher risk; good stability -> land is "predictable" and suitable for financing

## Single-season analysis - can we tell if it was farmed well or not?

**Yes - this is visible from the NDVI curve within the season:** **gradual rise** (planting/growth) -> **peak** -> **gradual decline** (harvest/end of cycle).

**A problematic season looks like this:**

- **Sudden drop** mid-season -> drought/irrigation issue/pest/stop/clearing
- **Weak plateau** all season -> weak growth (management/soil/water)
- **High fluctuation** -> irregular irrigation or observation issues (clouds handled by smoothing)

### Useful within-season metrics:

- **Within-season consistency**: how "normal" the season runs without sharp drops
- **Mid-season crash count**: number of strong collapses
- **Time-to-peak**: if very delayed -> slow growth/issues
- **Spatial uniformity over time:** persistent weak patches often indicate soil/salinity, while shifting weak areas over time often indicate irrigation or management.

**Reason:** this turns "images" into a decision: is season management good and stable or not.

## What the bank sees as output (clear outputs)

Instead of complex maps, a short report like this:

- **Land Status**: active / intermittent / inactive / encroachment
- **Soil/Land Condition (Proxy)**: Low / Med / High risk + reasons
- **2-Year Trend**: Improving / Stable / Declining
- **Season Performance**: Good / Interrupted / Weak
- **Flags**: Salinity? Waterlogging? Abandonment? Encroachment?
- **Portfolio View**: if the bank has many lands -> distribution of scores and risks at the portfolio level
    |<note> the last point reminded me that I did not think about the interface - how the company or bank will handle the application

### How an agri-financier uses FarmTrust in the financing cycle

The agri-financier uses FarmTrust as a decision-support tool, not as a system that issues an automatic decision.

Before financing, the system provides a clear historical view of the land (its activity, planting regularity, performance trend, and potential risks) that helps the financier assess readiness and risk.

During the financing period, FarmTrust is used for general monitoring and to detect any abnormal changes in land activity or season performance, with alerts when clear risk signals appear.

After the season or financing period ends, the financier can return to the land's recorded history and compare expected vs actual performance. This supports renewal, expansion, or re-evaluation decisions in the future.

**Simple, functional UX**:

The UX is built so the agri-financier understands the status in seconds. When they open the application, they see a list of financing requests/lands, each with a clear status color (ready / needs review / risk).

When they open a land, they see a **one-page summary**: top has the overall judgment, below it are a few short indicators (two-year trend, last season performance, flags), and each indicator has a simple tooltip explaining "why it came out this way".

The map is present but **not mandatory** - just an extra tab if they want to see location or weak patches.

No heavy tables or complex charts; the focus is on **summary + reason + confidence score**.

The goal is that the financier does not need to learn a new system, but can make decisions faster and with higher confidence.

The agri-financier can enter a land, for example, in two ways:

**(1) Draw directly on the map (Draw polygon):** draw land boundaries by hand on a simple map, and the system uses the drawing as the analysis region.

**(3) Point + approximate area:** place a pin on the land location and enter the approximate area (number of feddans), and the system creates an initial area of interest around the point.

> <note> this method can use a model that detects land or draws boundaries or even heuristics. If you put a point in the middle of the land, it will fill it and get the square that contains it.

## Optional medium-term addition: crop type and yield estimation (with caution)

### (A) Crop type

Very useful for the bank because risk differs by crop, but in Egypt: small plots, intercropping, and fast rotation; so "one crop with a specific name" can be misleading.

**Best starting point:**

- **Crop category:** winter / summer / perennial
- **Water-demand class:** high / medium / low
- **Season-length class:** short / medium / long
    **Why?** Easier technically + more useful for financing than an exact crop name at the beginning.

### (B) Yield estimation

High value but **sensitive to trust**: the bank may base a decision on a number, and if the number is wrong -> trust in the whole product is affected. Estimation usually needs ground truth yield data (even at village level), weather adjustment, and different models per crop/region.

**Safer alternative to start:**

- **Yield potential band:** low / medium / high
    or
- **Percentile** compared to neighbors (Top 25% / Mid / Bottom 25%)
    **Why?** It provides decision value without a hard-to-guarantee numeric "promise".

> <branch> Can we train a model on other regions that have online data (not just predicting from yield or RGB) and test it here?

## Additional metrics that support financing decisions

### (A) Land preparedness for financing

Is there a clear preparation period before planting? (fallow period + pattern change + irrigation start). Is the plot entering the season very late compared to the area?

### (B) Irrigation regularity

- regular or intermittent moisture/greenness pattern
- build a simple **Irrigation Regularity Score** from NDMI + NDVI stability

### (C) Explicit risk flags

- Waterlogging risk (flooding/poor drainage)
- Salinity risk
- Abandonment risk (long, repeated fallow periods)
- Encroachment risk (buildings/permanent land-use change)

### (D) Explainability (clear reasoning)

The bank likes a "reason" not just a number, such as:

- "a sudden drop in vegetation cover in mid-summer 2025"
- "recurring water pooling in the northwest corner 6 times over two years"
- "growth peak is declining gradually across 3 consecutive seasons"

## Indicators we propose (ordered)

### (A) "Crop health" indicators as a proxy for soil quality

- **NDVI / EVI**: vegetation vigor
- **Peak NDVI**: highest growth point in the season -> season strength indicator
- **Season AUC / Integral**: "total seasonal activity" (productivity proxy)
- **Spatial variability within the land**: if half the land is strong and half is weak -> likely irrigation/soil/leveling/local salinity issue
    **Reason:** the plant itself is a "sensor" that reveals management/soil/water quality without direct measurement.

### (B) Water/irrigation/drainage indicators

- **NDMI**: water stress indicator
- **NDWI / MNDWI**: detect standing water/ponding
- **Waterlogging frequency**: how often flooding/standing water appears in the same locations within the plot
    **Reason:** water issues (low irrigation or flooding) are among the biggest causes of season failure, and they are visible over time.

### (C) Heat and stress

- **LST**: surface temperature during growth
- **Heat-stress days**: days with high heat compared to neighbors at the same time
    **Reason:** in Egypt, heat stress + lack of irrigation causes performance drops, and heat adds a signal that aids interpretation.

### (D) Salinity (as a risk indicator)

- salinity indicators from visible/SWIR bands (depending on source)
- "white crust" pattern during fallow periods + persistence over time
- relative salinity map within the plot (persistent patches)
    **Reason:** salinity often creates "persistent weakness" in the same patches across multiple seasons.

### (E) Bare soil/preparation between seasons indicators

- **Bare Soil / Soil brightness indices**
- simple roughness/texture indicators
    **Reason:** between-season periods reveal things that are not visible during greenness.
## Final metrics list - MVP-Friendly (14 Metrics)
- **Active Agriculture Presence**
    - **Computed from:** Sentinel-2 (NDVI) 
    - **How calculated:** frequency of NDVI exceeding a minimum threshold with real green periods 
    - **Meaning for the bank:** the land has recent real agricultural activity 
    - **Recommendation:** eligible for financing / needs follow-up
- **Cropping Intensity**
    - **Computed from:** Sentinel-2 
    - **How calculated:** number of NDVI rise/fall cycles per year 
    - **Meaning for the bank:** land is planted once/twice/more per year 
    - **Recommendation:** higher intensity = higher potential return
- **Land Use Stability**
    - **Computed from:** Sentinel-2 
    - **How calculated:** stability of land use pattern (cultivated vs fallow/buildings) over time 
    - **Meaning for the bank:** land use is stable or changing 
    - **Recommendation:** instability = risk
- **Season Start Consistency**
    - **Computed from:** Sentinel-2 
    - **How calculated:** timing of green-up start compared to previous years and neighbors 
    - **Meaning for the bank:** entering the season at a normal time 
    - **Recommendation:** repeated delay = readiness/management issue
- **Peak Vegetation Strength**
    - **Computed from:** Sentinel-2 (Peak NDVI / EVI) 
    - **How calculated:** highest greenness value in the season 
    - **Meaning for the bank:** growth strength high/medium/low 
    - **Recommendation:** weak peak = lower potential productivity
- **Season Productivity (approximate index - AUC)**
    - **Computed from:** Sentinel-2 
    - **How calculated:** area under the NDVI curve over the season 
    - **Meaning for the bank:** total seasonal activity strong/medium/weak 
    - **Recommendation:** weak activity = lower return
- **Within-Season Stability**
    - **Computed from:** Sentinel-2 
    - **How calculated:** curve smoothness vs sharp drops within the season 
    - **Meaning for the bank:** season is stable or disrupted 
    - **Recommendation:** instability = operational risk
- **Mid-Season Shock Indicator**
    - **Computed from:** Sentinel-2 
    - **How calculated:** detect sudden NDVI drops during the season 
    - **Meaning for the bank:** sudden stop/problem during the season 
    - **Recommendation:** needs explanation or follow-up
- **Spatial Uniformity Index**
    - **Computed from:** Sentinel-2 
    - **How calculated:** NDVI variance within the plot over time 
    - **Meaning for the bank:** land is uniform or has weak patches 
    - **Recommendation:** persistent patches = soil/salinity issue
- **Irrigation Regularity (approximate index)**
    - **Computed from:** Sentinel-2 (NDMI) 
    - **How calculated:** moisture stability across the season 
    - **Meaning for the bank:** irrigation is regular or intermittent 
    - **Recommendation:** high fluctuation = season-failure risk
- **Waterlogging Risk**
    - **Computed from:** Sentinel-2 (NDWI / MNDWI) 
    - **How calculated:** repeated standing water in the same locations 
    - **Meaning for the bank:** flooding or poor drainage risk 
    - **Recommendation:** needs intervention/precaution
- **Salinity Risk (approximate index)**
    - **Computed from:** Sentinel-2 / Landsat 
    - **How calculated:** persistent weak patches with bright bare-soil signals 
    - **Meaning for the bank:** salinity likelihood 
    - **Recommendation:** long-term risk
- **Two-Year Trend Score**
    - **Computed from:** Sentinel-2 
    - **How calculated:** trend of Peak NDVI or AUC over two years 
    - **Meaning for the bank:** performance improving/stable/declining 
    - **Recommendation:** decline = re-evaluate financing
- **Neighbor Comparison Score**
    - **Computed from:** Sentinel-2 
    - **How calculated:** compare plot performance to neighbors in the same timing 
    - **Meaning for the bank:** better/weaker than surroundings 
    - **Recommendation:** below average = relative risk

## Full-Stack Portal details

Alongside analysis/backend, we need a clear **Portal** for the agri-financier to use outputs. This is a core part of the project even if the POC is "analysis".

### 1) Login + Users + Roles

- login
- simple roles:
    - **Admin**: manage accounts and permissions
    - **Analyst**: review results/data
    - **Loan Officer**: use reports to make decisions

### 2) Land Records Management

- add new land in two ways:
    - **Draw polygon on map**
    - **Pin + approximate area**
- each land has a fixed page with:
    - Summary (Status / Trend / Season / Flags)
    - Confidence level
    - Simple history (timeline/curve)
    - Export report (PDF or report page)

### 3) Case/Request Workflow (optional but useful)

Instead of just "lands", introduce a concept:

- **financing request** linked to a land (or more)
- request statuses: New -> Under Review -> Approved/Rejected
- notes inside the request (why accepted/rejected)

### 4) If there are pages outside the scope but overlapping with the MVP, we can mark them as under construction with a static page for that type or use a mockup

### 5) Backend ops (Ops Basics)

- when a land is added: a **Job** is created for analysis (Queue/Worker)
- error monitoring + retry
- store analysis outputs so the display is fast

> Idea: this Portal turns the analysis into a usable product, otherwise it stays a "model result" not a financing tool.
