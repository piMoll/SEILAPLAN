# build

### 0. Do security check
See: https://plugins.qgis.org/docs/security-scanning

```shell
# Install the security tools
pip install bandit detect-secrets flake8

# Run checks on your plugin directory
# Check if there are medium or high severity issues in the plugin, ignoring the lib folder
bandit -r SEILAPLAN/ -a vuln -f screen -x lib
# List only high severity issues in the plugin
bandit -r SEILAPLAN/ --severity-level high -a vuln -f screen -x lib
# Check if there are issues in the lib folder
bandit -r SEILAPLAN/lib --severity-level high -a vuln -f screen

# Check if there are secrets in the plugin
detect-secrets scan SEILAPLAN/

# Do a flake8 check on the plugin, ignoring the C901 error "too complex"
flake8 SEILAPLAN/ --ignore=C901
```

### 1. Create translation files
``` bash
cd SEILAPLAN
lrelease i18n/SeilaplanPlugin_de.ts i18n/SeilaplanPlugin_en.ts i18n/SeilaplanPlugin_fr.ts i18n/SeilaplanPlugin_it.ts
```

### 1. Update changelog

### 1. Change version information --> Version format: x.y.z
1. metadata.txt: Add short changelog with new title --> No need to change version, done automatically by ci-plugin
2. __init__.py: Change version
3. __init__.py: Set DEBUG to False
4. If template of field survey profile was changed, update its version

### 1. Create pull request with automatically attached plugin zip file

### 1. Do UI testing and Merge pull request

### 1. Create release on github
1. Create new tag with correct version x.y.z --> no "v" in the beginning!
2. Title: Seilaplan vx.y.z
3. Text: Add change log
4. Assets Will be created automatically by ci-plugin
