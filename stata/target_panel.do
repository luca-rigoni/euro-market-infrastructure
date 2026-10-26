* Replication in Stata of scripts/estimate_target_panel.py
* Run from the project root:  do stata/target_panel.do

capture log close
log using "output/target_panel_stata.txt", replace text

clear all
import delimited "data/processed/target_panel.csv", clear varnames(1)

drop if country == "DE"            // benchmark: its spread is zero by construction

gen mdate = monthly(month, "YM")
format mdate %tm
encode country, gen(cid)
xtset cid mdate

gen d_target_gdp = D.target_gdp    // missing after a gap, as in Python
gen d_spread = D.spread

* Country fixed effects (fe), month fixed effects (i.mdate), errors clustered by country
quietly xtreg d_target_gdp d_spread i.mdate, fe vce(cluster cid)
estimates store full
quietly xtreg d_target_gdp d_spread i.mdate if inrange(mdate, tm(2008m6), tm(2014m12)), fe vce(cluster cid)
estimates store crisis
quietly xtreg d_target_gdp d_spread i.mdate if inrange(mdate, tm(2015m1), tm(2026m6)), fe vce(cluster cid)
estimates store purchases

estimates table full crisis purchases, keep(d_spread) b(%9.3f) se(%9.3f) p(%9.3f) stats(N)

log close
