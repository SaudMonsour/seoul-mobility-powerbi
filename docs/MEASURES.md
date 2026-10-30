# Measure definitions

All measures are stored in the fact table and recalculate under active report filters.

## Total Rentals

```dax
SUM(FactDemand[Rentals])
```

Display format: `#,0`.

## Recorded Hours

```dax
COUNTROWS(FactDemand)
```

Display format: `#,0`.

## Operating Hours

```dax
SUM(FactDemand[OperatingFlag])
```

Display format: `#,0`.

## Non-operating Hours

```dax
[Recorded Hours] - [Operating Hours]
```

Display format: `#,0`.

## Rentals per Operating Hour

```dax
DIVIDE([Total Rentals], [Operating Hours])
```

Display format: `#,0.0`.

## Peak Single Hour

```dax
MAX(FactDemand[Rentals])
```

Display format: `#,0`.

## Average Temperature C

```dax
AVERAGE(FactDemand[TemperatureC])
```

Display format: `0.0"°C"`.

## Rainy Operating Hours

```dax
CALCULATE([Operating Hours], FactDemand[RainfallMm] > 0)
```

Display format: `#,0`.

## Rainy Operating Share

```dax
DIVIDE([Rainy Operating Hours], [Operating Hours])
```

Display format: `0.0%`.

## Operating Coverage

```dax
DIVIDE([Operating Hours], [Recorded Hours])
```

Display format: `0.0%`.

## Holiday Rentals

```dax
CALCULATE([Total Rentals], FactDemand[HolidayFlag] = 1)
```

Display format: `#,0`.

