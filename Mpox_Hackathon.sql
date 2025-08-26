CREATE TABLE mpox_tracker(
  country VARCHAR(30),
  report_date DATE,
  confirmed_cases INT,
  deaths INT,
  vaccinations_administered INT,
  active_surveillance_sites INT,
  suspected_cases INT,
  case_fatality_rate NUMERIC(6,4),
  clade VARCHAR(30),
  weekly_new_cases INT,
  vaccine_dose_allocated INT,
  vaccine_dose_deployed INT,
  vaccine_coverage NUMERIC(5,2),
  testing_laboratries INT,
  trained_chws INT,
  deployed_CHWs INT,
  surveillance_notes TEXT
)

SELECT * 
FROM mpox_tracker

/* 1. Objective 1 : Monitor Outbreak Trends and Hotspots
Track confirmed cases, suspected cases, deaths, and weekly new cases by country.
Identify countries with the highest case fatality rates (CFRs).
Spotlight regions where clade distribution may influence severity*/

--Track confirmed cases,suspected cases, deaths and weekly new case by country--
SELECT 
    country,
    SUM(suspected_cases) AS total_suspected,
    SUM(confirmed_cases) AS total_confirmed,
    ROUND(AVG(weekly_new_cases)) AS avg_weekly_cases,
	ROUND(SUM(deaths) * 100.0 / NULLIF(SUM(confirmed_cases), 0), 2) AS cfr_percent,
	RANK() OVER (ORDER BY SUM(deaths) * 100.0 / NULLIF(SUM(confirmed_cases), 0) DESC) AS rank,
    SUM(deaths) AS total_deaths
FROM mpox_tracker
GROUP BY country
ORDER BY total_confirmed DESC
LIMIT 5;
/*Uganda has more confirmed cases than Sierra Leone (31,160 > 30,225) → larger outbreak volume.
Sierra Leone has more deaths relative to its cases (1,302 deaths ÷ 30,225 cases ≈ 4.31%) → outbreak is deadlier.
That’s why CFR ranking is based on relative fatality, not absolute case numbers.

For stakeholder presentation, we can frame it like this:
Although Uganda has more confirmed cases than Sierra Leone, 
its lower CFR (1.82% vs 4.31%) indicates better case management or healthcare response. 
In contrast, Burundi and Sierra Leone, despite slightly lower case counts, have much higher CFRs, 
signaling urgent hotspots for CDC intervention.*/


--Which virus strains are associated with higher deaths or CFRs.--
SELECT
    country,
    clade,
    SUM(confirmed_cases) AS total_confirmed,
    SUM(deaths) AS total_deaths,
    ROUND( SUM(deaths) * 100.0 / NULLIF(SUM(confirmed_cases), 0), 2) AS cfr_percent,
	RANK() OVER (ORDER BY SUM(deaths) * 100.0 / NULLIF(SUM(confirmed_cases), 0) DESC) AS rank
FROM mpox_tracker
GROUP BY country, clade
ORDER BY country, cfr_percent DESC
LIMIT 5;


--Why is the Clade not known for Ethiopia--
SELECT country, SUM(confirmed_cases) AS total_confirmed, SUM(deaths) AS total_deaths
FROM mpox_tracker
WHERE clade IS NULL OR clade ILIKE 'unknown'
GROUP BY country
ORDER BY total_confirmed DESC;
/*Implications
Incomplete strain tracking
Without clade info, it’s impossible to tell if a more severe strain is circulating in these countries.
Potential underestimation of risk
If deaths occur in “unknown” clades, CFR by clade analysis may look lower than reality.
Priority for CDC action

These countries should be flagged for urgent genome sequencing or reporting improvements.*/
SELECT country, 
       SUM(confirmed_cases) AS total_confirmed, 
       SUM(deaths) AS total_deaths, 
       ROUND(SUM(deaths) * 100.0 / NULLIF(SUM(confirmed_cases),0),2) AS cfr_percent,
	   RANK() OVER (ORDER BY SUM(deaths) * 100.0 / NULLIF(SUM(confirmed_cases), 0) DESC) AS rank
FROM mpox_tracker
WHERE clade IS NULL OR clade ILIKE 'unknown'
GROUP BY country
ORDER BY total_confirmed DESC;
/*Countries like South Africa, Mozambique, Zambia, Kenya, Tanzania, Ethiopia report unknown clades. 
This represents a critical gap in genomic surveillance, 
which may hide high-risk variants and affects our ability to correlate clade with severity.*/

--OBJECTIVE 2 : Assess Vaccination Progress and Gaps---
/*
Compare vaccine doses allocated vs deployed vs administered.
Evaluate vaccine coverage by country.
Highlight countries with high allocations but low deployment/uptake.*/

-- Country-level vaccination summary + rates + stock gaps
WITH by_country AS (
  SELECT
    country,
    SUM(vaccine_dose_allocated)      AS allocated,
    SUM(vaccine_dose_deployed)       AS deployed,
    SUM(vaccinations_administered)   AS administered
  FROM mpox_tracker
  GROUP BY country
),
coverage AS (
  -- grab the *latest* coverage value per country
  SELECT DISTINCT ON (country)
         country,
         vaccine_coverage AS latest_coverage
  FROM mpox_tracker
  WHERE vaccine_coverage IS NOT NULL
  ORDER BY country, report_date DESC
)
SELECT
  bc.country,
  bc.allocated,
  bc.deployed,
  bc.administered,
  cv.latest_coverage,
  ROUND(bc.deployed     * 100.0 / NULLIF(bc.allocated,    0), 2) AS deployment_rate_pct,     -- deployed / allocated
  ROUND(bc.administered * 100.0 / NULLIF(bc.deployed,     0), 2) AS administration_rate_pct,  -- administered / deployed
  ROUND(bc.administered * 100.0 / NULLIF(bc.allocated,    0), 2) AS uptake_rate_pct,          -- administered / allocated
  (bc.allocated   - bc.deployed)     AS undeployed_stock,            -- still in central stock
  (bc.deployed    - bc.administered) AS stock_in_country_not_admin   -- in-country but not in arms
FROM by_country bc
LEFT JOIN coverage cv USING (country)
ORDER BY uptake_rate_pct ASC;   -- worst uptake at the top

/*Sierra Leone being a hotspot has the least vaccine allocation followed by Burundi
Why does Togo with low confirmed cases have more vaccine allocation*/

-- Compare Sierra Leone vs Togo: outbreak burden + vaccination stats + allocation efficiency
WITH by_country AS (
  SELECT
    country,
    SUM(confirmed_cases)           AS confirmed,
    SUM(deaths)                    AS deaths,
    SUM(vaccine_dose_allocated)    AS allocated,
    SUM(vaccine_dose_deployed)     AS deployed,
    SUM(vaccinations_administered) AS administered
  FROM mpox_tracker
  WHERE country IN ('Sierra Leone','Togo')
  GROUP BY country
),
coverage AS (
  -- get the *latest* coverage value for each country
  SELECT DISTINCT ON (country)
         country,
         vaccine_coverage AS latest_coverage
  FROM mpox_tracker
  WHERE country IN ('Sierra Leone','Togo')
    AND vaccine_coverage IS NOT NULL
  ORDER BY country, report_date DESC
)
SELECT
  bc.country,
  bc.confirmed,
  bc.deaths,
  ROUND(bc.deaths * 100.0 / NULLIF(bc.confirmed,0), 2) AS case_fatality_rate_pct,
  bc.allocated,
  bc.deployed,
  bc.administered,
  cv.latest_coverage,
  ROUND(bc.deployed     * 100.0 / NULLIF(bc.allocated,0), 2) AS deployment_rate_pct,
  ROUND(bc.administered * 100.0 / NULLIF(bc.deployed,0), 2)  AS administration_rate_pct,
  ROUND(bc.administered * 100.0 / NULLIF(bc.allocated,0), 2) AS uptake_rate_pct,
  (bc.allocated - bc.deployed)     AS undeployed_stock,
  (bc.deployed  - bc.administered) AS stock_in_country_not_admin,
  ROUND(bc.allocated * 1000.0 / NULLIF(bc.confirmed,0), 2) AS allocation_per_1000_cases
FROM by_country bc
LEFT JOIN coverage cv USING (country)
ORDER BY allocation_per_1000_cases DESC;

/*Insights from the numbers
Outbreak burden vs. allocation
Sierra Leone: 30,225 cases, 1,302 deaths (CFR 4.31% → higher severity).
Togo: 5,380 cases, 171 deaths (CFR 3.18% → lower severity).
Yet, Togo got more than double the vaccines (71k vs. 32k) despite having ~6× fewer cases.

Allocation efficiency (per 1,000 cases)
Togo: 13,281 doses per 1,000 cases - meaning over 13 doses per single case.
Sierra Leone: 1,089 doses per 1,000 cases - barely 1 dose per case.
This shows a severe imbalance: Togo has a surplus relative to its outbreak, 
while Sierra Leone is under-allocated despite being a hotspot.

Deployment and use of vaccines
Both countries are very good at actually using the doses they receive:
Deployment rate ~84%
Administration rate ~99%
Uptake ~83%
So, the issue is not operational capacity but upstream allocation decisions.

Coverage
Coverage in both countries is low (Sierra Leone 3.62%, Togo 4.22%).
Despite Togo having more vaccines, it has only slightly better coverage,
suggesting allocation did not prioritize outbreak burden but perhaps population size, equity considerations, or political negotiation factors.

Which means;
Mismatch in allocation vs. epidemiological need: Sierra Leone, with the largest burden, received disproportionately fewer vaccines.
Togo may be over-supplied relative to outbreak size, while Sierra Leone is under-supplied, raising concerns about equity and epidemic control strategy.
Both countries show strong efficiency in using what they get,so giving Sierra Leone more doses would likely translate into quick, effective coverage gains

Recommendations
Reallocation / Redistribution of doses
Advocate through Africa CDC for rebalancing of stock,excess supply in lower-burden countries (e.g., Togo) could be redirected to hotspots like Sierra Leone.
Data-driven allocation
Future allocation formulas should weight vaccine distribution by outbreak size and case fatality rate, not just population or political considerations.
Suggest using a “cases per dose” ratio metric (like your query showed) in allocation frameworks.
Support for Sierra Leone
Push for emergency surge allocation to Sierra Leone, given its higher deaths and higher CFR.
Highlight the country’s proven capacity (84% deployment, 99% administration) to assure donors that doses won’t be wasted.
Monitoring + advocacy
Use this data to prepare a policy brief for regional health authorities, showing the stark contrast (13,281 vs. 1,089 doses per 1,000 cases).
Recommend dynamic allocation reviews every month to avoid misalignments.*/

--Where is stock stuck—central vs in-country?--
WITH agg AS (
  SELECT
    country,
    SUM(vaccine_dose_allocated)    AS allocated,
    SUM(vaccine_dose_deployed)     AS deployed,
    SUM(vaccinations_administered) AS administered
  FROM mpox_tracker
  GROUP BY country
)
SELECT
  country,
  allocated,
  deployed,
  administered,
  (allocated - deployed)              AS undeployed_stock,              -- central bottleneck
  (deployed - administered)           AS in_country_unadministered,     -- last-mile bottleneck
  ROUND(deployed*100.0/NULLIF(allocated,0), 2)     AS deployment_rate_pct,
  ROUND(administered*100.0/NULLIF(deployed,0), 2)  AS administration_rate_pct,
  ROUND(administered*100.0/NULLIF(allocated,0), 2) AS uptake_rate_pct
FROM agg
ORDER BY in_country_unadministered DESC, undeployed_stock DESC
LIMIT 10;
/*This query shows deployment and administration rates are quite high everywhere (84–86% deployment, 94–98% administration).
That means: countries are generally good at using what they get.
But the allocation itself is not fair.
Cameroon and Ghana got tens of thousands of doses, while Sierra Leone hardly got any.
Uganda (a hotspot) is present in the data but the others with high allocations (Cameroon, Ghana, DR Congo, South Africa) are not hotspots.
So the problem is not inefficiency in Sierra Leone,it’s inequity in vaccine distribution at the global/regional allocation level.
Recommendations
Equity-based allocation: Redirect doses from non-hotspots with high undeployed stock (Cameroon, Ghana) toward hotspot countries with low allocations (Sierra Leone, Uganda).
Dynamic allocation model: Future allocations should be based on burden of disease (cases, hotspots)
Country’s demonstrated capacity to administer vaccines quickly (Sierra Leone is efficient with the little it gets)
Regional redistribution: Countries with large undeployed central stock (10k+ doses) could share with neighbors like Sierra Leone.
Monitoring system: Regular reporting of allocation vs uptake vs disease burden should guide mid-course corrections.*/

WITH agg AS (
  SELECT
    country,
    SUM(vaccine_dose_allocated)    AS allocated,
    SUM(vaccine_dose_deployed)     AS deployed,
    SUM(vaccinations_administered) AS administered
  FROM mpox_tracker
  GROUP BY country
)
SELECT
  country,
  allocated,
  deployed,
  administered,
  (allocated - deployed)              AS undeployed_stock,          -- central bottleneck
  (deployed - administered)           AS in_country_unadministered, -- last-mile bottleneck
  ROUND(deployed*100.0/NULLIF(allocated,0), 2)     AS deployment_rate_pct,
  ROUND(administered*100.0/NULLIF(deployed,0), 2)  AS administration_rate_pct,
  ROUND(administered*100.0/NULLIF(allocated,0), 2) AS uptake_rate_pct
FROM agg
ORDER BY in_country_unadministered ASC, undeployed_stock ASC
LIMIT 10;
/*Allocation inequity: Countries with high population burdens or hotspot status (like Sierra Leone and Uganda) are receiving disproportionately lower allocations compared to non-hotspot countries (e.g., Cameroon, Ghana, Togo).
Efficiency vs. equity gap: Deployment and administration rates are high and consistent across countries (~85% deployment, ~95% administration), so the issue is not country performance, but allocation decisions at the source.
Recommendations
Revisit allocation formulas: Factor in population size + hotspot status + efficiency track record, not just requests or initial submissions.
Reward efficiency: Countries like Sierra Leone that show high uptake like every other country and is a major uptake  should be prioritized for additional stock.
Redistribution mechanism: Surplus or underutilized stock (e.g., in Cameroon, Ghana) could be reallocated to countries with shortages.*/

--OBJECTIVE 3:Evaluate Surveillance and Workforce Capacity--
SELECT 
    country,
    SUM(active_surveillance_sites) AS total_active_sites,
    SUM(testing_laboratries) AS total_testing_labs,
    (SUM(active_surveillance_sites) + SUM(testing_laboratries)) AS total_surveillance_capacity,
    ROUND(AVG(case_fatality_rate), 2) AS avg_cfr
FROM mpox_tracker
GROUP BY country
ORDER BY total_surveillance_capacity ASC;
/*Burundi (408) and Sierra Leone (471) record the lowest surveillance capacities among the countries analyzed, falling far behind even the next country, Cameroon, which stands at 1,086. 
This indicates not just a low capacity but a significant structural gap in surveillance systems. 
Both countries also share an average case fatality rate (CFR) of 0.04, slightly higher than the 0.03 observed in most other countries. 
The combination of weak surveillance infrastructure and relatively elevated CFR suggests that delays in detection, limited laboratory coverage, and reduced outbreak monitoring capacity may be contributing factors. 
Taken together, these findings highlight that Sierra Leone and Burundi are not merely lagging but are critically under-resourced compared to their peers, making them particularly vulnerable hotspots for epidemic threats.*/



Select DISTINCT surveillance_notes
FROM mpox_tracker

SELECT * 
FROM mpox_tracker

SELECT 
    country,
    SUM(trained_chws) AS total_trained,
    SUM(deployed_chws) AS total_deployed,
	 ROUND(
        (SUM(deployed_chws)::numeric / NULLIF(SUM(trained_chws),0)) * 100, 
        2
    ) AS deployment_rate
FROM mpox_tracker
GROUP BY country
ORDER BY total_deployed ASC;
/*Sierra Leone and Burundi having being in the top 6 of countries with the lowest trained CHWs highlights the points made earlier on inequity in resource allocation
But why is Uganda with a 49155 total-deployed CHWs a hotspot 
Hypothesis could be POPULATION*/

WITH workforce AS (
    SELECT
        country,
        SUM(trained_chws) AS total_trained_chws,
        SUM(deployed_chws) AS total_deployed_chws,
        ROUND((SUM(deployed_chws)::numeric / NULLIF(SUM(trained_chws),0)) * 100, 2) AS deployment_rate_pct
    FROM mpox_tracker
    GROUP BY country
),
vaccines AS (
    SELECT
        country,
        SUM(vaccine_dose_allocated)    AS allocated,
        SUM(vaccine_dose_deployed)     AS deployed,
        SUM(vaccinations_administered) AS administered,
        ROUND(SUM(vaccine_dose_deployed)::numeric / NULLIF(SUM(vaccine_dose_allocated),0) * 100, 2) AS deployment_rate_pct,
        ROUND(SUM(vaccinations_administered)::numeric / NULLIF(SUM(vaccine_dose_deployed),0) * 100, 2) AS administration_rate_pct,
        ROUND(SUM(vaccinations_administered)::numeric / NULLIF(SUM(vaccine_dose_allocated),0) * 100, 2) AS uptake_rate_pct
    FROM mpox_tracker
    GROUP BY country
),
cases AS (
    SELECT
        country,
        SUM(confirmed_cases) AS total_cases,
        SUM(deaths)          AS total_deaths,
        ROUND((SUM(deaths)::numeric / NULLIF(SUM(confirmed_cases),0)) * 100, 2) AS cfr
    FROM mpox_tracker
    GROUP BY country
)
SELECT
    w.country,
    w.total_trained_chws,
    w.total_deployed_chws,
    w.deployment_rate_pct AS chw_deployment_pct,
    ROUND(w.total_trained_chws::numeric / NULLIF(c.total_cases,0), 2) AS trained_chws_per_case,
    ROUND(w.total_deployed_chws::numeric / NULLIF(c.total_cases,0), 2) AS deployed_chws_per_case,
    v.allocated,
    v.deployed AS vaccine_deployed,
    v.administered AS vaccine_administered,
    v.deployment_rate_pct AS vaccine_deployment_pct,
    v.administration_rate_pct AS vaccine_administration_pct,
    v.uptake_rate_pct AS vaccine_uptake_pct,
    c.total_cases,
    c.total_deaths,
    c.cfr
FROM workforce w
LEFT JOIN vaccines v USING (country)
LEFT JOIN cases c USING (country)
ORDER BY deployed_chws_per_case ASC;

/*This query shows that Population matters
Uganda has 47M people, Sierra Leone ~8M, Togo -9M, Ghana ~34M.
Absolute CHW numbers are misleading.
Even with a large CHW workforce, Uganda’s per-case coverage is diluted by its higher population and higher case numbers,
if Ghana can get 8 CHWS per case then Uganda can get more.
Smaller countries like Sierra Leone and Togo can achieve higher CHWs-per-case ratios more easily, 
so if Sierra Leone is still a hotspot, it highlights severe under-resourcing relative to its outbreak size.
Reccomendation
Stakeholder message
Per-case workforce ratio is a better indicator of outbreak preparedness than absolute CHWs or deployment %.
Countries with low CHWs per case relative to outbreak size should be prioritized for:
Additional workforce (surge CHWs)
Accelerated vaccination
Support for active surveillance & labs*/

--Countries with high cases but low workforce + surveillance + CFR--
WITH country_summary AS (
    SELECT
        country,
        SUM(confirmed_cases) AS total_cases,
        SUM(deployed_chws) AS total_deployed_chws,
        SUM(active_surveillance_sites) AS total_active_sites,
        ROUND((SUM(deployed_chws)::numeric / NULLIF(SUM(confirmed_cases),0)), 4) AS deployed_chws_per_case,
        ROUND((SUM(trained_chws)::numeric / NULLIF(SUM(confirmed_cases),0)), 4) AS trained_chws_per_case,
        ROUND((SUM(active_surveillance_sites)::numeric / NULLIF(SUM(confirmed_cases),0)), 4) AS surveillance_per_case
    FROM mpox_tracker
    GROUP BY country
)
SELECT *
FROM country_summary
WHERE 
    total_cases > (SELECT AVG(total_cases) FROM country_summary)
    AND deployed_chws_per_case < (SELECT AVG(deployed_chws_per_case) FROM country_summary)
    AND surveillance_per_case < (SELECT AVG(surveillance_per_case) FROM country_summary)
ORDER BY total_cases DESC;
/*This query further proves absolute numbers of CHWs, active sites, and surveillance capacity can be misleading.
Sierra Leone’s population is much smaller than Uganda’s, yet its confirmed cases are close to Uganda’s.
This means per capita or per case, Sierra Leone is far worse off, even if total CHWs deployed look moderately high.
Uganda, with a larger population, has more CHWs and surveillance sites, but its per-case ratios are still moderate, showing the country is stretched but better positioned than Sierra Leone or Burundi.
Nuance: Hotspots are not only defined by raw case numbers; they must be evaluated relative to both population and workforce/surveillance capacity.
Reccomendation
Focus should be on per-case ratios, not absolute numbers, to prioritize support.
Hotspots require targeted interventions: workforce surge, surveillance expansion, and proportionate vaccination.
Even countries with moderate total CHWs (like Sierra Leone) may be critically under-resourced relative to their outbreak size.
Data-driven allocation can help maximize impact of limited resources and move toward MPOC eradication.*/

--Understand Clade Distribution and Risk--
SELECT 
    country,
    clade,
    COUNT(*) AS records,
    SUM(confirmed_cases) AS total_cases,
    SUM(deaths) AS total_deaths
FROM mpox_tracker
GROUP BY country, clade
ORDER BY country, total_cases DESC;

SELECT
    clade,
    COUNT(DISTINCT country) AS affected_countries,
    SUM(confirmed_cases) AS total_cases,
    SUM(deaths) AS total_deaths,
    ROUND(SUM(deaths)*100.0/NULLIF(SUM(confirmed_cases),0),2) AS cfr_percent
FROM mpox_tracker
WHERE clade IS NOT NULL
GROUP BY clade
ORDER BY total_cases DESC;
/*These two queries show mortality is not solely driven by the clade,health system capacity, workforce, surveillance, and timely intervention are critical.
CLAD1 may have higher overall fatality, but weak health systems can make CLAD2 equally deadly in certain countries (like Sierra Leone).
Priority for intervention should combine:
Clade severity
Case burden
Healthcare and surveillance gaps
Recommendation
Hotspot countries should be prioritized regardless of clade, but special attention should be given to:
CLAD1 regions for rapid outbreak control.
Countries with low workforce or surveillance even if affected by CLAD2.
Allocate vaccine, CHWs, labs, and surveillance resources proportionate to both variant risk and system gaps.
*/

--Clade vs weekly new cases (trend over time)
SELECT DISTINCT
    report_date,
    clade,
    SUM(weekly_new_cases) AS weekly_cases
FROM mpox_tracker
WHERE clade IS NOT NULL
GROUP BY report_date, clade
ORDER BY report_date, weekly_cases DESC;
--Use a time trend grahp for this--
/*CLAD1 is spreading faster. Countries with weak health systems are most at risk. 
Strengthen workforce, surveillance, and vaccination where CLAD1 is dominant to prevent uncontrolled outbreaks and high fatalities
Recommendation
Prioritize hotspot countries affected by CLAD1 for:
Emergency deployment of CHWs and surveillance teams
Accelerated vaccination campaigns
Testing and lab expansion
Monitor weekly case trends per clade continuously to detect emerging variants or shifts in spread.*/

--Correlate Response Efforts with Outcomes--

SELECT
    country,
    SUM(confirmed_cases) AS total_cases,
    SUM(deaths) AS total_deaths,
    MAX(vaccine_coverage) AS latest_coverage,
    SUM(trained_chws) AS total_trained_chws,
    SUM(deployed_chws) AS total_deployed_chws,
    SUM(testing_laboratries) AS total_labs,
    SUM(weekly_new_cases) AS total_weekly_cases,
    
    -- Rates per confirmed case
    ROUND(SUM(deployed_chws)::numeric / NULLIF(SUM(confirmed_cases),0), 4) AS deployed_chws_per_case,
    ROUND(SUM(trained_chws)::numeric / NULLIF(SUM(confirmed_cases),0), 4) AS trained_chws_per_case,
    ROUND(SUM(testing_laboratries)::numeric / NULLIF(SUM(confirmed_cases),0), 4) AS labs_per_case,
    ROUND(SUM(weekly_new_cases)::numeric / NULLIF(SUM(confirmed_cases),0), 4) AS weekly_cases_per_case,
    ROUND(SUM(deaths)*100.0 / NULLIF(SUM(confirmed_cases),0),2) AS cfr_percent

FROM mpox_tracker
GROUP BY country
ORDER BY total_cases DESC;
/*Hotspots = high cases + insufficient workforce/surveillance/vaccine coverage.
Countries with high workforce per case (South Africa, Nigeria) experience low deaths despite cases, highlighting the importance of response capacity.
CFR and absolute deaths are amplified in countries with low resources even if the number of cases is similar.
Recommendation 
Focus resources on hotspots: Burundi, Sierra Leone, Uganda.
Deploy additional CHWs, labs, and vaccines proportional to case burden.
Use workforce-per-case ratios as a key metric for prioritization.
Monitor smaller countries with rising weekly cases, as they can become hotspots if resources are not scaled.*/

--Priority index--
WITH country_metrics AS (
    SELECT
        country,
        SUM(confirmed_cases) AS total_cases,
        SUM(deaths) AS total_deaths,
        MAX(vaccine_coverage) AS latest_coverage,
        SUM(trained_chws) AS total_trained_chws,
        SUM(deployed_chws) AS total_deployed_chws,
        SUM(testing_laboratries) AS total_labs,
        ROUND(SUM(deaths)*100.0/NULLIF(SUM(confirmed_cases),0),2) AS cfr_percent,
        ROUND(SUM(deployed_chws)::numeric / NULLIF(SUM(confirmed_cases),0),4) AS deployed_chws_per_case,
        ROUND(SUM(testing_laboratries)::numeric / NULLIF(SUM(confirmed_cases),0),4) AS labs_per_case
    FROM mpox_tracker
    GROUP BY country
)

SELECT
    country,
    total_cases,
    total_deaths,
    cfr_percent,
    latest_coverage,
    deployed_chws_per_case,
    labs_per_case,
    
    -- Priority Index formula (higher = worse situation)
    ROUND(
        (total_cases * 0.4) + 
        (total_deaths * 0.3) + 
        (100 - latest_coverage) * 0.1 + 
        (1 / NULLIF(deployed_chws_per_case,0)) * 0.1 + 
        (1 / NULLIF(labs_per_case,0)) * 0.1
    ,2) AS priority_index

FROM country_metrics
ORDER BY priority_index DESC
LIMIT 5;

/*Some countries are already burning (hotspots), others have sparks (high priority index). 
Workforce and vaccines are like firebreaks — we must reinforce them to prevent new hotspots
Hotspots need immediate intervention (Burundi, Uganda, Sierra Leone).
Countries like South Africa and Mozambique are watch closely: high priority index means they could escalate without sustained response.
Workforce and vaccination are mitigating factors — strengthening them is an effective prevention strategy.*/


SELECT
    country,
    COUNT(DISTINCT report_date) AS total_reports,
    surveillance_notes,
    SUM(confirmed_cases) AS total_cases,
    SUM(deaths) AS total_deaths
FROM mpox_tracker
WHERE country IN( 'Uganda','Sierra Leone') 
GROUP BY country, surveillance_notes
ORDER BY total_cases DESC;

SELECT 
    country,
    report_date,
    surveillance_notes,
    weekly_new_cases
FROM mpox_tracker
WHERE country IN ('Sierra Leone', 'Uganda')
AND surveillance_notes IN ('Increasing trend; surge teams deployed.','Declining trend; maintain surveillance intensity.')
ORDER BY country, report_date;
--Show this in a line graph--

SELECT 
    country,
    report_date,
    surveillance_notes,
    weekly_new_cases
FROM mpox_tracker
WHERE country IN ('Sierra Leone')
ORDER BY country, report_date;

SELECT 
    country,
    report_date,
    surveillance_notes,
    weekly_new_cases
FROM mpox_tracker
WHERE country IN ( 'Uganda')
ORDER BY country, report_date;

/*The queries above shows for Uganda
When weekly cases rose, the surveillance note shifted to “increasing trend → surge teams deployed.”
This suggests a responsive system: when cases spiked, they intensified surveillance.
Likely result → faster detection, isolation, and contact tracing → lower CFR despite high cases.
For Sierra Leone
Even when weekly cases surged, the surveillance note often stayed at stable trend → focused on case finding/contact tracing, instead of moving to surge deployment.
This suggests a slower or less aggressive response to surges.
Possible result → delays in detecting chains of transmission, late interventions, and overwhelmed local response → higher CFR relative to cases.
Reccomendations
Strengthen Surge Response Mechanisms
Ensure rapid escalation from stable surveillance to surge team deployment when weekly cases spike.
Develop clear thresholds (e.g., X% rise in weekly cases) that automatically trigger additional resources.
Improve Surveillance Flexibility
Move away from a one-size-fits-all stable surveillance approach.
Adopt adaptive surveillance that responds dynamically to case trends in real time.
nvest in Community Health Workforce (CHWs)
Train and equip CHWs to detect early signs of outbreak hotspots.
Expand CHW numbers in hard-to-reach areas to prevent hidden transmission chains.Prioritize Timeliness of Response
Donors and partners should support early deployment funds so that resources can be mobilized before the outbreak overwhelms systems.
Build rapid deployment teams with pre-positioned supplies for hotspots.*/

SELECT *
FROM mpox_tracker