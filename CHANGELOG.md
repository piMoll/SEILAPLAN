# SEILAPLAN Changelog

Languages: English | [Deutsch](CHANGELOG.de.md)

## Unreleased
### Fixes
- Infographics are displayed in English instead of German if the language is not recognized

### New Features
- Translation into Chinese, thanks to 蕭宇哲 / Bucks Valley Forestry, Taiwan
- Changelog in English

## Version 3.8.2 (August 2026)
### Fixes
- PDF export of the diagram automatically switches from landscape to portrait format when the cable line is very steep

## Version 3.8.1 (July 2026)
### New Features
- New Seilaplan logo
- Remove "experimental" plugin status

### Fixes
- Hide scrollbar in the "Parameters" and "Bird's eye view" tabs when the editing window is large enough
- Prevent switching to the two-cable system in the editing window when the cable system runs uphill
- Detect and handle invalid support spans of 0 meters length during cable line calculation

## Version 3.8.0 (June 2026)
### New Features
- Export of geodata in GeoPackage format (*.gpkg)
- PDF export of the diagram in A4 and A3 paper formats
- Relative storage of paths to elevation data in the SEILAPLAN project file, allowing projects and elevation data to be moved and reopened together
- User interface improvements
    - Improved scrolling in the editing window when there are many supports and limited available space
    - Display a loading symbol at the mouse cursor during long-running processes (e.g. saving or loading)
    - Less prominent display of question mark buttons
    - Improved colors and contrasts in the user interface and diagram in QGIS Dark Mode
    - Renamed tabs in the start window from "Optimization #1" and "Optimization #2" to "Optimization" and "Miscellaneous"
    - Clearer highlighting of the warning "...skyline lifts off the saddle at least on one support" in the editing window
- Output a warning when the parameter "Ground clearance: to be respected after / up to …" is set to 0 m and the structural element "Anchor" has been selected at the same time
- Improved and more sensitive detection of favorable terrain shapes for support positioning during optimization
- Various maintenance work, code quality improvements, and automation of the release process

### Fixes
- Map is correctly centered on raster layer, even when multiple rasters are selected in the selection list
- Contour lines can now also be calculated from Cloud Optimized GeoTIFF rasters (COG)
- New versions of the SEILAPLAN plugin are recognized again by the Plugin Manager and can be updated

## Version 3.7.1 (August 2025)
### Fixes
- Under Qt 6, no cable line can be defined after selecting the raster

## Version 3.7.0 (July 2025)
### New Features
- Upgrade for use under QGIS 4.0 and Qt 6 (from October 2025)
- Move to the official QGIS plugin repository (existing users do not need to do anything)

### Fixes
- Fix an issue preventing the use of XYZ rasters
- Fix error message when deleting support symbols on the map
- Enable loading of SEILAPLAN project files containing Cloud Optimized GeoTIFFs (COG)
- Various maintenance work

## Version 3.6.4 (March 2025)
### Fixes
- Plugin crashes when supports are edited or deleted in the editing window

## Version 3.6.3 (November 2024)
### Fixes
- Summary report: Section "Span and anchor fields" shows the same support designation twice (from -> to)
- Bird's eye view: Point number from terrain profile not visible
- Editing window: Attachment point is only updated when changes to support properties are confirmed with the Enter key
- Editing window: Plugin crashes when the inclination of support is changed

## Version 3.6.2 (September 2024)
### Fixes
- Plugin window size cannot be resized on macOS

## Version 3.6.1 (August 2024)
### Fixes
- Missing intermediate supports when loading a project file
- Editing window: Stop diagram resets to full view when cable line is recalculated

## Version 3.6.0 (August 2024)
### New Features
- Seilaplan can be launched multiple times to edit projects (or variants) in parallel
- New parameters to define limits for empty and loaded rope deflection angles (previously fixed at 1/3° and 30/60°)
- New parameter to define the height of the attachment point above the skyline saddle (previously fixed at 1.5 m)
- Editing window:
  - Additional parameters (DBH, sag, deflection angle, etc.) can be displayed in the diagram via a drop-down list
  - In the new "Parameters" tab, the parameter set can be changed
  - In the diagram, cable sag is now output individually for each span instead of once for the entire cable line
  - Min. attachment point diameter is specified for each support
  - Support designations can now be 42 instead of 22 characters long. Readability of designations in the exported diagram has been improved
- Bird's eye view: Adjusted symbol for multi-tree anchors; anchor ropes end at the start / end point of the cable line, not behind it
- Exported PDFs (diagram, reports) include the unique name of the project folder
- The automatically generated project name includes the year and is formatted similar to ISO
- Various improvements to user guidance: adjustment of labels and addition of hints

### Fixes
- Summary report: Correction of angle of attack calculation for pass-through end supports
- Default value for parameter 'Attachment point above skyline saddle' is now 3.0 m instead of previously 1.5 m; the value is customizable
- Fix an issue when generating diagram PDFs that causes older QGIS versions to crash
- Profile lines are always inserted at the top of the QGIS layer tree instead of at the currently selected layer
- The plugin window stays in the foreground when drawing on the map (macOS)

## Version 3.5.3 (May 2024)
### Fixes
- Error starting the plugin on Windows with QGIS version 3.36 due to a missing scipy library

## Version 3.5.2 (March 2024)
### Fixes
- Bird's eye view
  - Correct support symbols when they should be oriented to the right of the cable and towards the start point
  - Adjust order of support types in selection list: support types first, then anchor types

## Version 3.5.1 (January 2024)
### Fixes
- Bird's eye view: Revise support symbols, adjust length of anchor ropes
- Add parameters in the editing window: Show maximum cable tension at the highest point in the diagram
- Bug: Moving a support to the end or start of the profile causes a plugin crash

## Version 3.5.0 (August 2023)
### New Features
- Bird's eye view: Representation of cable line, supports, and anchor ropes from a bird's eye view
  - Configure support category and position, as well as anchor rope orientation in a new tab
  - Export bird's eye view as a diagram below the profile
  - Addition of support properties in reports and geodata export
- Display background map: For QGIS projects in the Swiss coordinate system, the Swiss national map is now loaded instead of the OSM map

## Version 3.4.2 (June 2023)
### Fixes
- Terrain profile from Haglöf Vertex: Add location of the first measurement (point no. 0)
- Correct the display of the diameter symbol in reports
- Fix issue in the generation of profile lines for cable lines in direction 0, 100, 200, or 300 gon
- When loading reportlab (report generation library), the system-installed version is preferred

## Version 3.4.1 (December 2022)
### New Features
- Export terrain line as DXF, KML, and Shapefile
- Export profile view (side view) as DXF
- Redesign of the save dialog window
- Save geodata to separate folders

### Fixes
- Summary report: Corrected value for maximum cable - ground clearance
- Haglöf Vertex CSV import: Only consider measurements of type "TRAIL", display "3P" measurements as additional information in the terrain profile
- Fixed error message when creating QGIS layers

## Version 3.4.0 (May 2022)
### New Features
- Profile import from field survey protocol, including protocol template in Excel format
- Selection and import of terrain profile in a separate dialog window
- Template for profiles in CSV format with X, Y, Z coordinates
- Increase of maximum allowable values for: payload weight (now 250 kN), minimum breaking load of skyline (now 5000 kN), skyline tension at start point (now 1000 kN)

### Fixes
- Better handling of errors during terrain profile import
- Selection list for rasters no longer shows WMS layers
- Better handling of errors during raster data preparation
- Improved formatting of coordinate values for international users
- Map markers for fixed supports reliably disappear after deletion

## Version 3.3.0 (January 2022)
### New Features
- Recording and saving project metadata such as author, project number, forest location, etc. Project metadata is listed in reports
- Project settings are now saved in JSON format instead of text format (legacy project settings in text format are still supported)
- Revision and standardization of various technical terms in the German version
- Display of parameters in the editing window diagram: Parameters are now always displayed regardless of whether the threshold is exceeded
- Default setting for start and end points of the cable line is now an anchor instead of a support

### Fixes
- Report content is only partially visible or displaced when a cable line without intermediate supports or with anchors only is created
- Report content is only partially visible or displaced when more than 7 supports are listed
- In parameter set "MSK 3t 20/11/8mm", cable diameter was corrected from 22 to 20 mm
- Support type (anchor, support, yarder) is read correctly from project settings
- When creating terrain profiles from Vertex files, relative distance and angle measurements are now used for calculation instead of GPS measurements. GPS measurements are only used for georeferencing the profile.
- When opening the terrain line window, an empty diagram was shown
- Parameter sets disappear after plugin update. This issue occurs once during update to version 3.3.0, and will not occur in the future.
  - Note: You can restore lost parameter sets by loading old project files calculated with that parameter set.

## Version 3.2.1 (June 2021)
### New Features
- Error message during plugin installation in QGIS 3.20 / 3.16.8
- Raster layers are not selected in dropdown list when loading a project file

## Version 3.2 (June 2021)
### New Features
- Multi-selection of raster tiles: Multiple raster layers can now be selected, allowing cable lines to be constructed across tile boundaries

### Fixes
- Correction of angle of attack calculation for 0 meter high supports

## Version 3.1 (November 2020)
### New Features
- Introduction of machine parameter "Initial tension"
- Specification of attachment point diameter in summary report

### Fixes
- Various bug fixes

## Version 3.0 (September 2020)
### New Features
- Redesign of the plugin and addition of further input parameters
- Extension with manual editing options for the cable line
- Translation to EN, IT, FR

## Version 2.0 (February 2018)
Porting to QGIS 3

## Version 1.0 (May 2015)
Initial version
