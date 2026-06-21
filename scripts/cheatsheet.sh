
# get new translation texts
cd SEILAPLAN
bash i18n/update-strings.sh SeilaplanPlugin_de SeilaplanPlugin_en SeilaplanPlugin_fr SeilaplanPlugin_it
## This does not work properly, dont use it!
## The script will set some translations to "obsolete" because it can't
##  find the tr() calls in the code. Also, it will remove all translator
##  comments.

# compile translations
cd SEILAPLAN
lrelease i18n/SeilaplanPlugin_de.ts i18n/SeilaplanPlugin_en.ts i18n/SeilaplanPlugin_fr.ts i18n/SeilaplanPlugin_it.ts


# Sort imports
pre-commit run --all-files isort

# Check for big issues
pre-commit run --all-files flake8
