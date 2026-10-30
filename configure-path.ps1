$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataRoot = (Resolve-Path (Join-Path $Root 'data\clean')).Path + '\'
$ModelFile = Join-Path $Root 'powerbi\Dashboard.SemanticModel\model.bim'
$Model = Get-Content -LiteralPath $ModelFile -Raw -Encoding UTF8 | ConvertFrom-Json
$Parameter = $Model.model.expressions | Where-Object { $_.name -eq 'DataRoot' }
$Parameter.expression = '"' + $DataRoot.Replace('"', '""') + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ModelFile, ($Model | ConvertTo-Json -Depth 100), $Utf8)
Write-Host 'DataRoot configured. Open powerbi\Dashboard.pbip in Power BI Desktop and refresh.'
