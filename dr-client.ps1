# ==============================================================================
# DR DEFICIENCY MANAGEMENT SYSTEM - PowerShell Client
# ==============================================================================
# A Windows-native client (no Python required) for PostgreSQL database access.
#
# REQUIREMENTS:
# - PostgreSQL ODBC Driver (psqlODBC) - will be downloaded if not present
# - PowerShell 5.1+ (built into Windows 10+)
#
# CONFIGURATION:
# Edit the DB_CONFIG section below to match your database settings.
# ==============================================================================

# ==============================================================================
# DATABASE CONFIGURATION - EDIT THESE VALUES
# ==============================================================================
$DB_CONFIG = @{
    Host     = "172.24.2.46"
    Port     = "5432"
    Database = "maintenance_app"
    User     = "postgres"
    Password = "pwneaw139"
}

# ==============================================================================
# GLOBAL VARIABLES
# ==============================================================================
$Global:DbConnection = $null

# ==============================================================================
# UI HELPERS
# ==============================================================================
function Clear-Host-Custom {
    Clear-Host
}

function Show-Header {
    param([string]$Title)

    $width = 80
    Write-Host ""
    Write-Host $("+" + ("-" * $width) + "+") -ForegroundColor Cyan
    Write-Host $("|" + $Title.PadCenter($width) + "|") -ForegroundColor Cyan
    Write-Host $("+" + ("-" * $width) + "+") -ForegroundColor Cyan
}

function Show-Menu {
    Clear-Host-Custom
    Show-Header "DR DEFICIENCY MANAGEMENT SYSTEM"

    Write-Host ""
    Write-Host "  [1] View Recent Deficiencies" -ForegroundColor Yellow
    Write-Host "  [2] Search Deficiencies" -ForegroundColor Yellow
    Write-Host "  [3] Add New Deficiency" -ForegroundColor Yellow
    Write-Host "  [4] Update Deficiency Status" -ForegroundColor Yellow
    Write-Host "  [5] Delete Deficiency" -ForegroundColor Yellow
    Write-Host "  [0] Exit Application" -ForegroundColor Red
    Write-Host ""
    Write-Host $("+" + ("-" * 80) + "+") -ForegroundColor Cyan
}

function Show-Alert {
    param(
        [string]$Message,
        [string]$Type = "Info"  # Info, Success, Error, Warning
    )

    $color = switch ($Type) {
        "Success" { "Green" }
        "Error"   { "Red" }
        "Warning" { "Yellow" }
        default   { "White" }
    }

    Write-Host ""
    Write-Host "  [$Type] $Message" -ForegroundColor $color
}

function Show-Table {
    param(
        [array]$Headers,
        [array]$Rows
    )

    if ($Rows.Count -eq 0) {
        Write-Host ""
        Write-Host "  [ NO RECORDS FOUND ]" -ForegroundColor Yellow
        Write-Host ""
        return
    }

    # Calculate column widths
    $colWidths = @()
    for ($i = 0; $i -lt $Headers.Count; $i++) {
        $width = $Headers[$i].Length
        foreach ($row in $Rows) {
            $cellValue = if ($row[$i] -eq $null) { "" } else { [string]$row[$i] }
            # Truncate for display
            if ($cellValue.Length -gt 35 -and $i -eq 3) {
                $cellValue = $cellValue.Substring(0, 32) + "..."
            }
            $width = [Math]::Max($width, $cellValue.Length)
        }
        $colWidths += [Math]::Min($width, 40)  # Max width 40
    }

    # Create separator
    $separator = "+"
    foreach ($w in $colWidths) {
        $separator += "+" + ("-" * ($w + 2))
    }
    $separator += "+"

    # Create row format
    $rowFormat = "|"
    foreach ($w in $colWidths) {
        $rowFormat += " {0,-$w} |"
    }

    Write-Host ""
    Write-Host $separator -ForegroundColor Cyan
    Write-Host ($rowFormat -f $Headers) -ForegroundColor Cyan
    Write-Host $separator -ForegroundColor Cyan

    foreach ($row in $Rows) {
        $values = @()
        for ($i = 0; $i -lt $row.Count; $i++) {
            $val = if ($row[$i] -eq $null) { "" } else { [string]$row[$i] }
            if ($val.Length -gt 35 -and $i -eq 3) {
                $val = $val.Substring(0, 32) + "..."
            }
            $values += $val.PadRight($colWidths[$i]).Substring(0, [Math]::Min($val.Length, $colWidths[$i]))
        }
        Write-Host ($rowFormat -f $values)
    }

    Write-Host $separator -ForegroundColor Cyan
    Write-Host ""
}

# ==============================================================================
# DATABASE OPERATIONS
# ==============================================================================
function Test-ODBCDriver {
    # Check if PostgreSQL ODBC driver is installed
    $drivers = Get-OdbcDriver -Name "*ostgreSQL*" -ErrorAction SilentlyContinue
    return ($drivers -ne $null -and $drivers.Count -gt 0)
}

function Install-ODBCDriver {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "PostgreSQL ODBC Driver Not Found!" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The PostgreSQL ODBC driver is required to connect to the database."
    Write-Host ""
    Write-Host "Please download and install from:"
    Write-Host "https://www.postgresql.org/ftp/odbc/versions/msi/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Look for the latest version and download the MSI installer."
    Write-Host "After installation, restart this script." -ForegroundColor Yellow
    Write-Host ""

    # Try to open the download page
    try {
        Start-Process "https://www.postgresql.org/ftp/odbc/versions/msi/"
    } catch {
        # Ignore if browser fails to open
    }

    Read-Host "Press Enter to exit"
    exit 1
}

function Get-ConnectionString {
    $driver = (Get-OdbcDriver -Name "*ostgreSQL*" -ErrorAction SilentlyContinue | Select-Object -First Object).Name
    if (-not $driver) {
        $driver = "PostgreSQL Unicode"
    }

    return "Driver={$driver};Server=$($DB_CONFIG.Host);" +
           "Port=$($DB_CONFIG.Port);" +
           "Database=$($DB_CONFIG.Database);" +
           "Uid=$($DB_CONFIG.User);" +
           "Pwd=$($DB_CONFIG.Password);"
}

function Open-Database {
    param([switch]$Quiet)

    try {
        $connStr = Get-ConnectionString
        $Global:DbConnection = New-Object System.Data.Odbc.OdbcConnection($connStr)
        $Global:DbConnection.Open()

        if (-not $Quiet) {
            Show-Alert "Database connected successfully!" -Type Success
        }
        return $true
    }
    catch {
        if (-not $Quiet) {
            Show-Alert "Database connection failed: $($_.Exception.Message)" -Type Error
            Write-Host ""
            Write-Host "Troubleshooting:" -ForegroundColor Yellow
            Write-Host "1. Ensure PostgreSQL ODBC driver is installed" -ForegroundColor White
            Write-Host "2. Check if database server is reachable: $($DB_CONFIG.Host):$($DB_CONFIG.Port)" -ForegroundColor White
            Write-Host "3. Verify credentials in DB_CONFIG" -ForegroundColor White
        }
        return $false
    }
}

function Close-Database {
    if ($Global:DbConnection -ne $null) {
        if ($Global:DbConnection.State -eq 'Open') {
            $Global:DbConnection.Close()
        }
        $Global:DbConnection.Dispose()
        $Global:DbConnection = $null
    }
}

function Invoke-SQL {
    param(
        [string]$Query,
        [array]$Parameters = $null
    )

    if ($Global:DbConnection -eq $null -or $Global:DbConnection.State -ne 'Open') {
        if (-not (Open-Database -Quiet)) {
            throw "Database not connected"
        }
    }

    try {
        $cmd = $Global:DbConnection.CreateCommand()
        $cmd.CommandText = $Query

        if ($Parameters -ne $null) {
            for ($i = 0; $i -lt $Parameters.Count; $i++) {
                $param = $cmd.CreateParameter()
                $param.ParameterName = "@param$i"
                $param.Value = $Parameters[$i]
                $cmd.Parameters.Add($param) | Out-Null
            }
        }

        $reader = $cmd.ExecuteReader()
        $table = New-Object System.Data.DataTable
        $table.Load($reader)

        $reader.Close()
        $cmd.Dispose()

        return $table
    }
    catch {
        throw "SQL Error: $($_.Exception.Message)"
    }
}

function Invoke-SQLNonQuery {
    param(
        [string]$Query,
        [array]$Parameters = $null
    )

    if ($Global:DbConnection -eq $null -or $Global:DbConnection.State -ne 'Open') {
        if (-not (Open-Database -Quiet)) {
            throw "Database not connected"
        }
    }

    try {
        $cmd = $Global:DbConnection.CreateCommand()
        $cmd.CommandText = $Query

        if ($Parameters -ne $null) {
            for ($i = 0; $i -lt $Parameters.Count; $i++) {
                $param = $cmd.CreateParameter()
                $param.ParameterName = "@param$i"
                $param.Value = $Parameters[$i]
                $cmd.Parameters.Add($param) | Out-Null
            }
        }

        $rows = $cmd.ExecuteNonQuery()
        $cmd.Dispose()

        return $rows
    }
    catch {
        throw "SQL Error: $($_.Exception.Message)"
    }
}

# ==============================================================================
# CRUD OPERATIONS
# ==============================================================================
function Read-Deficiencies {
    Show-Header "READ: LATEST DEFICIENCIES"

    try {
        $query = @"
SELECT "DeficiencyNumber", "SiteName", "Resource", "Issue_Description", "Status", "Severity", "RaisedByName"
FROM dr_deficiency
ORDER BY "DeficiencyNumber" DESC
LIMIT 10;
"@

        $table = Invoke-SQL -Query $query

        $rows = @()
        foreach ($row in $table.Rows) {
            $displayRow = @(
                $row["DeficiencyNumber"],
                $row["SiteName"],
                $row["Resource"],
                $row["Issue_Description"],
                $row["Status"],
                $row["Severity"],
                $row["RaisedByName"]
            )
            $rows += ,$displayRow
        }

        $headers = @("Def.Num", "Site", "Resource", "Description", "Status", "Severity", "Raised By")
        Show-Table -Headers $headers -Rows $rows
    }
    catch {
        Show-Alert $_.Exception.Message -Type Error
    }
}

function Search-Deficiencies {
    Show-Header "SEARCH: DEFICIENCY DATABASE"
    Write-Host " Search across ID, Site, Resource, Issue Description, or Submitter."

    $searchTerm = Read-Host " Enter keyword"

    if ([string]::IsNullOrWhiteSpace($searchTerm)) {
        Show-Alert "Search term cannot be empty." -Type Warning
        return
    }

    try {
        $query = @"
SELECT "DeficiencyNumber", "SiteName", "Resource", "Issue_Description", "Status", "Severity", "RaisedByName"
FROM dr_deficiency
WHERE CAST("DeficiencyNumber" AS VARCHAR) LIKE ?
   OR LOWER("SiteName") LIKE LOWER(?)
   OR LOWER("Resource") LIKE LOWER(?)
   OR LOWER("Issue_Description") LIKE LOWER(?)
   OR LOWER("RaisedByName") LIKE LOWER(?)
ORDER BY "DeficiencyNumber" DESC
LIMIT 20;
"@

        $likeTerm = "%$searchTerm%"
        $params = @($likeTerm, $likeTerm, $likeTerm, $likeTerm, $likeTerm)

        $table = Invoke-SQL -Query $query -Parameters $params

        $rows = @()
        foreach ($row in $table.Rows) {
            $displayRow = @(
                $row["DeficiencyNumber"],
                $row["SiteName"],
                $row["Resource"],
                $row["Issue_Description"],
                $row["Status"],
                $row["Severity"],
                $row["RaisedByName"]
            )
            $rows += ,$displayRow
        }

        Write-Host ""
        Write-Host "  [ SEARCH RESULTS FOR: '$searchTerm' ]" -ForegroundColor Cyan
        $headers = @("Def.Num", "Site", "Resource", "Description", "Status", "Severity", "Raised By")
        Show-Table -Headers $headers -Rows $rows
    }
    catch {
        Show-Alert $_.Exception.Message -Type Error
    }
}

function Create-Deficiency {
    Show-Header "CREATE: NEW DEFICIENCY"
    Write-Host "Enter the details below. For this terminal client, core fields are requested."
    Write-Host "Other required schema fields will be auto-populated with defaults."
    Write-Host ""

    $siteName = (Read-Host " Site Name (max 3 chars)").Substring(0, [Math]::Min(3, (Read-Host " Site Name (max 3 chars)").Length))
    Write-Host " Site Name (max 3 chars) : " -NoNewline
    $siteName = Read-Host
    if ($siteName.Length -gt 3) { $siteName = $siteName.Substring(0, 3) }

    Write-Host " Deficiency Number (int) : " -NoNewline
    $defNum = Read-Host

    Write-Host " Resource (max 5 chars)  : " -NoNewline
    $resource = Read-Host
    if ($resource.Length -gt 5) { $resource = $resource.Substring(0, 5) }

    Write-Host " Issue Description        : " -NoNewline
    $issueDesc = Read-Host

    Write-Host " Severity (max 3 chars)  : " -NoNewline
    $severity = Read-Host
    if ($severity.Length -gt 3) { $severity = $severity.Substring(0, 3) }

    Write-Host " Raised By Name          : " -NoNewline
    $raisedBy = Read-Host

    # Validation
    if ([string]::IsNullOrWhiteSpace($siteName) -or
        [string]::IsNullOrWhiteSpace($defNum) -or
        [string]::IsNullOrWhiteSpace($resource) -or
        [string]::IsNullOrWhiteSpace($issueDesc) -or
        [string]::IsNullOrWhiteSpace($severity) -or
        [string]::IsNullOrWhiteSpace($raisedBy)) {
        Show-Alert "All fields are required." -Type Warning
        return
    }

    $defNumInt = 0
    if (-not [int]::TryParse($defNum, [ref]$defNumInt)) {
        Show-Alert "Deficiency Number must be numeric." -Type Warning
        return
    }

    try {
        $currentDate = (Get-Date).ToString("yyyy-MM-dd")
        $currentTimestamp = Get-Date

        $query = @"
INSERT INTO dr_deficiency (
    "SiteName", "DeficiencyNumber", "Resource", "Issue_Description", "Type",
    "Severity", "CategoryName", "Status", "RaisedByName", "RaisedDate",
    "EnteredByName", "EnteredDate", "DueDate", "DashboardVisible", "DeficiencyType",
    "Is_Restricted", "Is_Safety", "Affects_Qualification", "UniqueDBIdentifier",
    "fldResourceId", "fldRaisedById", "fldEnteredById", "fldRaisedDate", "fldDueDate",
    "Customer", "_RaisedDate", "_EnteredDate", "_DueDate"
) VALUES (?, ?, ?, ?, 'Standard',
    ?, 'General', 'OPEN', ?, ?,
    'System', ?, ?, TRUE, 'Operational',
    FALSE, FALSE, FALSE, ?,
    1, 1, 1, ?, ?,
    'Internal', ?, ?, ?)
"@

        $params = @(
            $siteName, $defNumInt, $resource, $issueDesc,
            $severity, $raisedBy, $currentDate,
            $currentDate, $currentDate, $defNumInt,
            $currentTimestamp, $currentTimestamp, $currentDate
        )

        Invoke-SQLNonQuery -Query $query -Parameters $params
        Show-Alert "Record inserted successfully." -Type Success
    }
    catch {
        Show-Alert $_.Exception.Message -Type Error
    }
}

function Update-Deficiency {
    Show-Header "UPDATE: DEFICIENCY STATUS"

    Write-Host " Enter Deficiency Number to update: " -NoNewline
    $defNum = Read-Host

    Write-Host " Enter New Status (e.g., CLOSED)  : " -NoNewline
    $newStatus = Read-Host

    if ([string]::IsNullOrWhiteSpace($defNum) -or [string]::IsNullOrWhiteSpace($newStatus)) {
        Show-Alert "Both fields are required." -Type Warning
        return
    }

    $defNumInt = 0
    if (-not [int]::TryParse($defNum, [ref]$defNumInt)) {
        Show-Alert "Deficiency Number must be numeric." -Type Warning
        return
    }

    try {
        $query = 'UPDATE dr_deficiency SET "Status" = ? WHERE "DeficiencyNumber" = ?'
        $params = @($newStatus, $defNumInt)

        $rows = Invoke-SQLNonQuery -Query $query -Parameters $params

        if ($rows -gt 0) {
            Show-Alert "Deficiency $defNum updated to $newStatus." -Type Success
        } else {
            Show-Alert "Deficiency $defNum not found." -Type Warning
        }
    }
    catch {
        Show-Alert $_.Exception.Message -Type Error
    }
}

function Delete-Deficiency {
    Show-Header "DELETE: REMOVE DEFICIENCY"

    Write-Host " Enter Deficiency Number to delete: " -NoNewline
    $defNum = Read-Host

    if ([string]::IsNullOrWhiteSpace($defNum)) {
        Show-Alert "Deficiency Number is required." -Type Warning
        return
    }

    $defNumInt = 0
    if (-not [int]::TryParse($defNum, [ref]$defNumInt)) {
        Show-Alert "Deficiency Number must be numeric." -Type Warning
        return
    }

    Write-Host " Are you sure you want to delete $defNum? (Y/N): " -NoNewline -ForegroundColor Yellow
    $confirm = Read-Host

    if ($confirm -eq "Y" -or $confirm -eq "y") {
        try {
            $query = 'DELETE FROM dr_deficiency WHERE "DeficiencyNumber" = ?'
            $params = @($defNumInt)

            $rows = Invoke-SQLNonQuery -Query $query -Parameters $params

            if ($rows -gt 0) {
                Show-Alert "Deficiency $defNum deleted." -Type Success
            } else {
                Show-Alert "Deficiency $defNum not found." -Type Warning
            }
        }
        catch {
            Show-Alert $_.Exception.Message -Type Error
        }
    } else {
        Show-Alert "Deletion cancelled." -Type Info
    }
}

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================
function Main {
    # Check for ODBC driver
    if (-not (Test-ODBCDriver)) {
        Install-ODBCDriver
    }

    # Connect to database
    if (-not (Open-Database)) {
        Read-Host "Press Enter to exit"
        exit 1
    }

    while ($true) {
        Show-Menu
        Write-Host " Select an option: " -NoNewline
        $choice = Read-Host

        switch ($choice) {
            '1' {
                Clear-Host-Custom
                Read-Deficiencies
                Read-Host " Press Enter to return to menu"
            }
            '2' {
                Clear-Host-Custom
                Search-Deficiencies
                Read-Host " Press Enter to return to menu"
            }
            '3' {
                Clear-Host-Custom
                Create-Deficiency
                Read-Host " Press Enter to return to menu"
            }
            '4' {
                Clear-Host-Custom
                Update-Deficiency
                Read-Host " Press Enter to return to menu"
            }
            '5' {
                Clear-Host-Custom
                Delete-Deficiency
                Read-Host " Press Enter to return to menu"
            }
            '0' {
                Clear-Host-Custom
                Write-Host ""
                Write-Host "  Closing connection. Goodbye." -ForegroundColor Green
                Write-Host ""
                Close-Database
                exit 0
            }
            default {
                Clear-Host-Custom
                Show-Alert "Invalid option. Please select 0-5." -Type Warning
                Start-Sleep -Milliseconds 1500
            }
        }
    }
}

# ==============================================================================
# EXTENSION METHOD FOR STRING CENTERING
# ==============================================================================
Update-TypeData -TypeName System.String -MemberName PadCenter -MemberType ScriptMethod -Value {
    param($width)
    $pad = ($width - $this.Length) / 2
    $this.PadLeft($this.Length + [Math]::Floor($pad)).PadRight($width)
} -Force

# ==============================================================================
# ENTRY POINT
# ==============================================================================
try {
    Main
}
finally {
    Close-Database
}
