# execute everything in plugin/

# [deprecated] Compile resources
#pyrcc5 -o resources/resources.py resources/resources.qrc

# [deprecated] Compile gui -> ui files are  loaded directly via uic.loadUiType()
#pyuic5 gui/seilaplanDialog.ui -o gui/ui_seilaplanDialog.py
#pyuic5 gui/adjustmentDialog.ui -o gui/ui_adjustmentDialog.py
#pyuic5 gui/surveyImportDialog.ui -o gui/ui_surveyImportDialog.py

# When DEBUG is True, the resources path in ui files is removed, so loadUiType() works.
# When opening the ui file in the QtDesigner, resources have to be selected again.

# get new translation texts
bash scripts/update-strings.sh SeilaplanPlugin_de SeilaplanPlugin_en SeilaplanPlugin_fr SeilaplanPlugin_it
## This does not work properly, dont use it!
## The script will set some translations to "obsolete" because it can't
##  find the tr() calls in the code. Also, it will remove all translator
##  comments.

# compile translations
# Currently, this needs a conda env with Python 3.9, since the ubuntu 24.04 
#  system python is at 3.12 and there are no pyqt6 tools currently for this version
lrelease SeilaplanPlugin_de.ts SeilaplanPlugin_en.ts SeilaplanPlugin_fr.ts SeilaplanPlugin_it.ts


