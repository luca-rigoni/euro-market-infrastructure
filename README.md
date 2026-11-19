# Euro area market infrastructure: TARGET balances and Eurosystem collateral

![tests](https://github.com/luca-rigoni/euro-market-infrastructure/actions/workflows/tests.yml/badge.svg)

This project uses public ECB data to study two pieces of the Eurosystem's market infrastructure:

1. **TARGET balances and sovereign spreads.** A country-month panel of the TARGET balances of
   11 euro area national central banks (2008–2026), estimated with fixed effects in Python and
   replicated in Stata.
2. **The Eurosystem collateral list.** 190 monthly snapshots (each month-end from April 2010 to
   December 2025, plus 23 October 2026) of the list of marketable assets eligible as collateral in
   Eurosystem credit operations: 5,852,527 asset-month records, cleaned from three different file
   formats and stored in SQLite.

Data are downloaded from the ECB Data Portal API and the ECB website, stored in a SQLite database,
analysed in Python (pandas, linearmodels, matplotlib) and Stata, and checked by 19 automated tests
that run on GitHub Actions at every push.

## Background: the TARGET Services

The Eurosystem operates the infrastructure through which central bank money moves in the euro area:

- **T2**, the real-time gross settlement system for large-value payments and central bank operations
  (the successor of TARGET2);
- **TIPS** (TARGET Instant Payment Settlement), for instant payments in central bank money;
- **T2S** (TARGET2-Securities), the common platform where central securities depositories (CSDs)
  settle securities transactions against central bank money;
- **ECMS** (Eurosystem Collateral Management System), which manages the assets that banks pledge
  as collateral to obtain central bank credit;
- **Pontes**, the Eurosystem's solution for settling transactions recorded on distributed ledger
  technology (DLT) platforms in central bank money.

Part 1 of the project looks at T2 through the balances it generates between national central banks;
part 2 looks at the assets that feed collateral management.

---

## Part 1 – TARGET balances and sovereign spreads

When a payment from a bank in Italy to a bank in Germany is settled in T2, the Banca d'Italia
acquires a liability towards the Eurosystem and the Bundesbank a claim. The net position of each
national central bank is its **TARGET balance**. Large negative balances appeared during the
sovereign debt crisis, when deposits left the countries under stress, and again with the asset
purchase programmes, when the liquidity created by purchases ended up in accounts held in a few
financial centres.

![TARGET balances](figures/target_balances.png)

### Data

| Variable | ECB dataset | Series key (CC = country) | Frequency |
|---|---|---|---|
| TARGET balance of the national central bank, end of month | TGB | `M.CC.N.A094T.U2.EUR.E` | monthly, from May 2008 |
| 10-year government bond yield (convergence criterion) | IRS | `M.CC.L.L40.CI.0000.EUR.N.Z` | monthly |
| Nominal GDP, seasonally adjusted | MNA | `Q.Y.CC.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.V.N` | quarterly |

Countries: AT, BE, DE, ES, FI, FR, GR, IE, IT, NL, PT (Luxembourg is excluded as a financial-centre
outlier). TARGET balances are expressed in percent of annual GDP (sum of the last four quarters,
repeated in the three months of each quarter); spreads are measured against the German 10-year yield.
The panel has 2,397 country-months, May 2008 – June 2026: 218 months for each country except Greece,
whose 10-year yield is missing in the ECB series for July 2015, the month in which Greek banks were
closed and capital controls introduced.

### Model

For country *i* and month *t* (Germany excluded, since its spread is zero by construction):

Δ(TARGET balance / GDP)<sub>it</sub> = β · Δspread<sub>it</sub> + a<sub>i</sub> + g<sub>t</sub> + e<sub>it</sub>

The model is estimated in first differences because balances and spreads are highly persistent.
Month fixed effects g<sub>t</sub> absorb everything common to all countries in a month (ECB
decisions, global shocks), so β compares countries in the same month; country fixed effects
a<sub>i</sub> absorb country-specific trends. Standard errors are computed in two ways:

- **clustered by country**, which allows any correlation over time within a country. With only
  10 countries (clusters) this estimator is imprecise, so the Stata do-file, which replicates the
  regression with `xtreg, fe`, applies a small-sample correction and takes p-values from a
  t distribution with 9 degrees of freedom;
- **Driscoll–Kraay**, which also allows correlation across countries in the same month and relies
  on the number of months (217) rather than the number of countries; its p-values, computed in
  Python, come from the normal distribution.

### Results

| Sample | β | Clustered SE (Stata) | Clustered p-value (Stata) | Driscoll–Kraay SE | Driscoll–Kraay p-value | Observations |
|---|---|---|---|---|---|---|
| Full sample, 2008–2026 | −0.706 | 0.321 | 0.055 | 0.318 | 0.027 | 2,168 |
| Crisis years, 2008–2014 | −0.652 | 0.345 | 0.092 | 0.305 | 0.033 | 790 |
| Asset purchase years, 2015–2026 | −1.224 | 0.419 | 0.017 | 0.705 | 0.083 | 1,378 |

A one-point increase in a country's spread over Germany is associated with a fall in its TARGET
balance of about 0.7 percent of GDP in the same month, relative to the other countries. The
coefficient is negative in every sample, and Python and Stata give the same estimates. How
significant it is depends on the standard errors:

- with errors **clustered by country** (Stata), the estimate is significant at 5% only after 2015
  (p = 0.017), and at 10% in the full sample (0.055) and in the crisis years (0.092);
- with **Driscoll–Kraay** errors the ranking is reversed: the full sample and the crisis years are
  significant at 5% (p = 0.027 and 0.033), while after 2015 the standard error is almost twice the
  clustered one and the larger coefficient is significant only at 10% (p = 0.083).

No sample is therefore significant at 5% with both estimators: the evidence points in one direction
but is not conclusive. Python's clustered standard errors, computed without Stata's small-sample
correction, are slightly smaller (0.305, 0.330 and 0.399, in `output/target_panel_results.csv`), and
their p-values come from the normal distribution; with only 10 clusters, the Stata version of the
clustered p-values is the more reliable one. The regression describes an
association, not a causal effect: stress in a country raises its spread and drives deposits out of
its banks at the same time.

---

## Part 2 – The Eurosystem list of eligible marketable assets

The ECB publishes every working day the full list of marketable assets that banks can pledge as
collateral, with yearly archives back to April 2010. Each record is one asset (identified by its
ISIN) with its haircut category, asset type, currency, issuer and guarantor type, issuer residence,
central securities depository, coupon type, maturity and haircut. The data contain no amounts, so the
analysis counts assets rather than their value.

### Cleaning

`scripts/fetch_collateral.py` downloads the 16 yearly archives for 2010–2025 (3–4 GB) and keeps
the last file of each month, i.e. the last working day. The archive for 2026 was not yet published
when the data were collected, so the snapshot of 23 October 2026 was downloaded separately from the
ECB's eligible assets page (see *How to run*). `src/collateral.py` turns every snapshot into the same table:

- **Three containers:** `ea_all_*.tgz` (April 2010 – June 2013, a tar archive with a text file
  inside), `ea_all_*.txt.gz` (July 2013 – May 2015) and `ea_csv_*.csv.gz` (from June 2015). All
  are tab-separated text encoded in UTF-16.
- **Renamed columns:** the settlement location moves from `COUNTRY_OF_LOCATION` to `ISSUER_CSD` in
  May 2014; the category from `LIQUIDITY_CLASS` to `HAIRCUT_CATEGORY` and the haircut from
  `VALUATION_HAIRCUT` to `HAIRCUT` in September 2015. A single mapping (`COLUMNS`) gives the old and
  the new names the same schema, and a test checks that an asset written in the old and in the new
  format produces identical rows.
- **Codes:** countries are extracted from codes such as `IRFR` (issuer residence) and `CLFR01` (CSD);
  dates are converted to ISO format; haircuts to numbers.
- **Validation:** every ISIN is checked against its check digit (Luhn algorithm) and duplicates within
  a snapshot are dropped. Of the 5,852,546 records read, 19 were dropped: test records with an empty
  ISIN in the snapshot of 29 February 2012. No duplicates were found.
- **Pitfalls avoided:** all fields are read as text, so codes are not turned into numbers, and
  pandas' default list of missing-value markers is switched off. Otherwise the string "NA", which the
  ECB's dictionary of eligible assets uses as the country code of Namibia, would become a missing
  value, and empty fields (for example the issuer residence of supranational issuers) would become
  NaN instead of empty text. No Namibian asset appears in the 190 snapshots, so this choice changes
  no result, but it keeps the files exactly as published.

The 190 snapshots are stored in the table `eligible_assets` with primary key `(snapshot_date, isin)`;
loading a month again replaces its rows instead of duplicating them.

### Results

![Eligible assets by haircut category](figures/collateral_composition.png)

The list shrank from 44,043 assets in April 2010 to about 30,000 from 2016 and stands at 31,340 in
October 2026. Its composition changed: category IV, which today contains unsecured bank debt, fell
from 64% to 48% of the assets, category II almost tripled (from 3,028 to 9,104 assets), and
asset-backed securities (category V) fell from 1,650 to 581.

![Monthly changes](figures/collateral_turnover.png)

Comparing consecutive snapshots separates assets that leave the list because they mature from
assets removed while still outstanding, which reflect eligibility decisions. A test on a small invented database checks that this split is computed correctly. The largest movements match changes in the collateral framework:

| Month | What the data show | Related change in the collateral framework |
|---|---|---|
| December 2010 | 13,004 assets removed before maturity, almost all bank debt in category IV, including assets in US dollars and pounds sterling | End of the temporary expansion of October 2008, which had admitted bank debt traded on certain non-regulated markets and assets in US dollars, pounds sterling and yen (eligible until December 2010) |
| December 2011 | 12,165 assets added, almost all euro-denominated debt of banks in category IV (medium-term notes, commercial paper and certificates of deposit, bonds), mostly listed on non-regulated markets such as the French market for negotiable medium-term notes and STEP; about 4,300 of them had been removed in December 2010 | From 1 January 2012 debt instruments issued by credit institutions no longer need to be admitted to trading on a regulated market (recast General Documentation, Guideline ECB/2011/14, announced on 21 September 2011); the assets already appear in the snapshot of 30 December 2011, the last working day before the new rule applied |
| November 2012 | Additions include more than 500 assets in US dollars | Assets in US dollars, pounds sterling and yen admitted again (decision of 6 September 2012) |
| December 2018 | 5,320 assets removed before maturity, mostly unsecured bank bonds | End of the transition to the new rules for unsecured bank bonds decided in December 2017: bonds not meeting them, including those issued by entities outside the EU, became ineligible, and eligible unsecured bank bonds fell by more than €400 billion |
| June 2023 | 3,218 assets change category, of which 2,997 covered bonds move from category III to II and about 70 assets from II to I | From 29 June 2023 all covered bonds are assigned to category II and EU bonds move to category I |

About one asset in four (21–30% over the period) is settled in a CSD located outside the issuer's
country. Almost nine in ten of these are held in the two international CSDs, Euroclear Bank and
Clearstream Banking, which the list records with the code `CLBL01`; among the assets settled in a
national CSD, only 2–6% use one outside the issuer's country. The share shows no break in May 2014,
when the source field changes from `COUNTRY_OF_LOCATION` to `ISSUER_CSD`, which supports the
harmonisation.

The tables behind the figures are saved in `output/` as CSV files.

---

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.build_database          # download TARGET, yield and GDP series into SQLite
python -m scripts.build_target_panel      # build the country-month panel
python -m scripts.estimate_target_panel   # panel regressions (Python)
python -m scripts.plot_target
# in Stata, from the project root:  do stata/target_panel.do

python -m scripts.fetch_collateral        # yearly archives 2010–2025 -> 189 month-end snapshots (3–4 GB download)
# the 190th snapshot, ea_csv_261023.csv.gz (23 October 2026), was downloaded by hand from the
# ECB's eligible assets page and saved in data/raw/collateral/
python -m scripts.build_collateral_db     # clean and load the 190 snapshots into SQLite
python -m scripts.analyse_collateral      # tables and figures

pytest                                    # 19 tests, no internet connection needed
```

## Structure

```
src/        download.py (ECB API), database.py (SQLite), target.py (panel), collateral.py (cleaning)
scripts/    one script per step of the pipeline
stata/      target_panel.do (replication of the panel regression)
tests/      tests of the download, database, panel construction, cleaning and turnover
output/     result tables (CSV) and the Stata log
figures/    figures used in this README
```

## Limitations

- TARGET balances are aggregate positions of national central banks, not transaction-level data.
- The collateral list contains no amounts outstanding or amounts pledged, and month-end snapshots
  miss changes that are reversed within a month. For 2026 only the October snapshot is used,
  because the yearly archive is not yet available, so no monthly changes are computed between
  December 2025 and October 2026.

## Sources

- ECB Data Portal: [TARGET balances (TGB)](https://data.ecb.europa.eu/data/datasets/TGB/data-information),
  long-term interest rates (IRS), national accounts (MNA).
- ECB: [eligible assets database and archive](https://www.ecb.europa.eu/mopo/coll/assets/html/list-MID.en.html).
- ECB press releases of [17 October 2008](https://www.ecb.europa.eu/press/pr/date/2008/html/pr081017_2.en.html),
  [21 September 2011](https://www.ecb.europa.eu/press/pr/date/2011/html/pr110921.en.html),
  [6 September 2012](https://www.ecb.europa.eu/press/pr/date/2012/html/pr120906_2.en.html) and
  [20 December 2022](https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.pr221220_1~ca6ca2cc09.en.html);
  [Guideline ECB/2011/14](https://www.ecb.europa.eu/ecb/legal/pdf/l_33120111214en000100951.pdf)
  (OJ L 331, 14.12.2011); SUERF Policy Note, [The Eurosystem collateral framework in 2018 and 2019](https://www.suerf.org/policynotes/17311/the-eurosystem-collateral-framework-in-2018-and-2019).

## Use of AI

Parts of the code were drafted and revised with the help of an AI assistant. I reviewed and ran all of
it, adapted it to my existing modules, and checked the results against the data, the tests and,
for the panel regression, an independent replication in Stata.
