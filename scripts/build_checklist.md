# build

### 1. Update changelog

### 2. Change version information --> Version format: x.y.z
1. metadata.txt: Change version, add short changelog with new title
2. plugin.xml: Change version in _<pyqgis_plugin>_ and _<download_url>_
3. __init__.py: Change version
4. __init__.py: Set DEBUG to False 
5. If template of field survey profile was changed, update it's version


### 3. Check if build configs are still up to date
1. pb_tool.cfg
2. build.py


### 4. Add git tag with new version


### 5. Run build script to deploy plugin to a different QGIS profile, create zip file and exclude all unnecessary files
```python3 build.py qgis_profile='PluginTest'```


### 6. Merge dev into master


### 7. Create release on github
1. Title: Seilaplan vx.y.z
2. Text: Add change log
3. Assets: Add Seilaplan.zip file
