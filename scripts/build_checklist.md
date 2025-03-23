# build

### 1. Update changelog

### 2. Change version information --> Version format: x.y.z
1. metadata.txt: Change version, add short changelog with new title
2. plugin.xml: Change version in _<pyqgis_plugin>_ and _<download_url>_
3. __init__.py: Change version
4. __init__.py: Set DEBUG to False 
5. If template of field survey profile was changed, update its version


### 3. Check if include and exclude list in build.py is still up-to-date


### 4. Add git tag with new version


### 5. Run build script to deploy plugin to a zip in the parent folder
###    of the plugin dir
```python3 build.py```


### 6. Merge dev into master


### 7. Create release on github
1. Title: Seilaplan vx.y.z
2. Text: Add change log
3. Assets: Add Seilaplan.zip file
