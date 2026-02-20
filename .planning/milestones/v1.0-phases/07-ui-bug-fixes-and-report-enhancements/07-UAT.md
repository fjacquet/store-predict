---
status: complete
phase: 07-ui-bug-fixes-and-report-enhancements
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md]
started: 2026-02-19T14:00:00Z
updated: 2026-02-19T14:00:00Z
---

## Current Test

number: 1
name: Upload LiveOptics file and see performance data in review table
expected: |
  Upload samples/live-optics.xlsx. On the Review page, the AG Grid table should show new columns: "Description", "Peak IOPS", "8K Eq. IOPS", and "Peak MB/s" with numeric values populated for most VMs.
awaiting: user response

## Tests

### 1. Upload LiveOptics file and see performance data in review table
expected: Upload samples/live-optics.xlsx. On the Review page, the AG Grid table should show new columns: "Description", "Peak IOPS", "8K Eq. IOPS", and "Peak MB/s" with numeric values populated for most VMs.
result: [pass]

### 2. Upload RVTools file — performance columns hidden
expected: Upload samples/rvtools.xlsx. On the Review page, the performance columns (Peak IOPS, 8K Eq. IOPS, Peak MB/s) should NOT appear since RVTools has no performance data. The "Description" column should still be visible (populated from Annotation field if data exists).
result: [pass]

### 3. Multi-row selection with checkboxes
expected: On the Review page, each row should have a checkbox on the left. Clicking checkboxes selects multiple rows. A header checkbox selects/deselects all. Row clicks should still open the workload edit dialog (not select).
result: [pass]

### 4. Filter preservation after workload edit
expected: On the Review page, set a column filter (e.g., filter OS column to "Windows"). Then change a workload on one of the filtered VMs via inline dropdown. After the edit, the filter should remain active — you should still see only filtered results, not all VMs.
result: [pass]

### 5. Page preservation after workload edit
expected: On the Review page with pagination, navigate to page 2 or 3. Change a workload on a VM via inline dropdown. After the edit, you should remain on the same page, not jump back to page 1.
result: [pass]

### 6. Subcategory selection in inline dropdown
expected: Click to edit a workload_category cell. The dropdown should show full "Category / Subcategory" labels (e.g., "Database / Microsoft SQL", "Database / Oracle"). Selecting one should update both the category and subcategory, and recalculate the DRR.
result: [pass]

### 7. Unknown (Reducible) VMs are editable
expected: Find a VM classified as "Unknown (Reducible)". Click its workload cell to edit. The dropdown should appear and let you reassign it to any workload. The DRR should update accordingly.
result: [pass]

### 8. PDF report includes VM statistics
expected: Complete the flow to the Report page. Download the PDF. The report should contain an "VM Statistics" section showing: average VM size and largest VM name with its size.
result: [pass]

### 9. PDF report includes performance summary (LiveOptics)
expected: With LiveOptics data loaded, download the PDF. The report should contain a "Performance Summary" section showing: Total Peak IOPS, Total Average IOPS, Peak Throughput (MB/s), and Total 8K Equivalent IOPS.
result: [pass]

### 10. Classification uses description field as fallback
expected: This is an internal behavior test. If a VM has a generic name (e.g., "SRV001") but its Annotation/Description mentions "Oracle Database", the classifier should detect Oracle via description fallback. You can verify by checking if VMs with descriptive annotations get better classification than "Unknown (Reducible)".
result: [skipped]

## Summary

total: 10
passed: 9
issues: 0
pending: 0
skipped: 1

## Gaps

[none yet]
