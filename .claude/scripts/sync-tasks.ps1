# Sync tasks to GitHub as sub-issues
param(
    [string]$EpicNumber = "1",
    [string]$Repo = "B30780/AOI_inference_agent",
    [string]$EpicPath = ".claude\epics\aoi-inference-agent"
)

$taskMappings = @()

Get-ChildItem "$EpicPath\[0-9][0-9][0-9].md" | ForEach-Object {
    $taskFile = $_.FullName
    $oldNum = $_.BaseName
    
    # Extract task name from frontmatter
    $taskName = (Select-String -Path $taskFile -Pattern '^name: (.+)$' | Select-Object -First 1).Matches.Groups[1].Value
    
    # Strip frontmatter
    $content = Get-Content $taskFile -Raw
    $lines = $content -split "`n"
    $inFrontmatter = $false
    $skipCount = 0
    $bodyLines = foreach($line in $lines) {
        if($line -match '^---$') {
            $skipCount++
            if($skipCount -eq 2) {
                $inFrontmatter = $false
                continue
            }
            $inFrontmatter = $true
            continue
        }
        if(-not $inFrontmatter -and $skipCount -eq 2) {
            $line
        }
    }
    
    $body = $bodyLines -join "`n"
    $bodyFile = "$env:TEMP\task-$oldNum-body.md"
    $body | Out-File -Encoding utf8 $bodyFile
    
    Write-Host "Creating task $oldNum - $taskName"
    
    try {
        # Create sub-issue (output goes to console)
        $output = gh sub-issue create `
            --parent $EpicNumber `
            --title $taskName `
            --body (Get-Content $bodyFile -Raw) `
            --label "task,epic:aoi-inference-agent" `
            --repo $Repo 2>&1 | Out-String
        
        # Extract issue number from output
        if($output -match 'https://github.com/.*/issues/(\d+)') {
            $taskNumber = $Matches[1]
            $taskMappings += [PSCustomObject]@{
                OldNum = $oldNum
                File = $taskFile
                Number = $taskNumber
                Name = $taskName
            }
            Write-Host "  ✓ Created: #$taskNumber"
        } else {
            Write-Host "  ✗ Failed to extract issue number"
            Write-Host "  Output: $output"
        }
    } catch {
        Write-Host "  ✗ Error: $_"
    }
}

Write-Host "`n=== Task Mappings ==="
$taskMappings | Format-Table -AutoSize

# Save mappings to file
$mappingsFile = "$EpicPath\task-mappings.json"
$taskMappings | ConvertTo-Json | Out-File -Encoding utf8 $mappingsFile
Write-Host "`nMappings saved to: $mappingsFile"

return $taskMappings
