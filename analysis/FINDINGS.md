# Analysis findings

The source spans 365 complete dates and 8,760 unique hourly records. It contains 6,172,314 rentals, with 8,465 operating hours and 295 non-operating hours.

## Demand picture

- Average demand over operating hours: 729.2 rentals/hour.
- Largest single observed hour: 3,556 rentals.
- Highest average hourly slot: 18:00, approximately 1,554.0 rentals per operating hour.
- Summer averages 1,034.1 rentals per operating hour; winter averages 225.5.
- Rain-recorded operating hours average 167.3 rentals, compared with 765.6 for hours without recorded rain.

Weather is correlated with season, temperature, calendar and operating schedules. The rain comparison is descriptive and is not a causal weather effect. June 2018 has the largest monthly count, 896,887 rentals.

## Cleaning judgment

No source cells are missing and no exact records repeat. Dates are explicitly parsed as day/month/year, unit-bearing columns are standardized, and source visibility units are multiplied by ten to express metres. Every non-operating record is retained with its zero-rental observation and a flag.

Using operating hours as a denominator avoids confusing closure with low demand. Zero operating-hour selections return a blank ratio in Power BI, rather than an infinite or fabricated zero-demand rate. The dataset has no available-fleet capacity, so rental counts cannot be labeled fleet utilization or unmet demand. Extremes are retained, not clipped.
