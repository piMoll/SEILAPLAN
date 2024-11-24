from qgis.PyQt.QtCore import QEventLoop, QUrl
from qgis.core import QgsFileDownloader


class FileFetcher:
    
    def __init__(self, url, filePath):
        self.url = QUrl(url)
        self.filePath = filePath
        self.success = False
        self.run()
        
    def error(self):
        self.success = False

    def canceled(self):
        self.success = False

    def completed(self):
        self.success = True

    def run(self):
        # Run file download in separate event loop
        loop = QEventLoop()
        downloader = QgsFileDownloader(self.url, self.filePath, delayStart=True)
        downloader.downloadExited.connect(loop.quit)
        downloader.downloadError.connect(self.error)
        downloader.downloadCanceled.connect(self.canceled)
        downloader.downloadCompleted.connect(self.completed)
        downloader.startDownload()
        loop.exec()
