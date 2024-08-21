import os


def remove_resource_location():
    """Go through all *.ui files in gui folder and remove the resources.qrc
    location path. Because of it, the ui file can't be read properly via the
    uic.loadUiType() function.
    This script is called automatically when the plugin is in DEBUG mode
    (see flag in __init__.py)."""
    pluginPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    guiPath = os.path.join(pluginPath, "gui")
    
    for file in os.listdir(guiPath):
        if file.endswith(".ui"):
            uiFilePath = os.path.join(guiPath, file)
            with open(uiFilePath, 'r') as f:
                ui_content = f.read()
            ui_content = ui_content.replace('<include location="resources.qrc"/>', '')
            with open(uiFilePath, 'w') as f:
                f.write(ui_content)
        

if __name__ == '__main__':
    remove_resource_location()
