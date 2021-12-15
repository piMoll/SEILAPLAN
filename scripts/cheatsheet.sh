# execute everything in plugin/

# Compile resources
pyrcc5 -o resources/resources.py resources/resources.qrc

# Compile gui
pyuic5 ui/sgd_dockwidget_base.ui -o ui/sgd_dockwidget_base.py

# get new translation texts
bash scripts/update-strings.sh de en fr it
## This does not work properly, dont use it!
## The script will set some translations to "obsolete" because it can't
##  find the tr() calls in the code. Also, it will remove all translator
##  comments.

# compile translations
bash bash scripts/update-strings.sh SeilaplanPlugin_de


