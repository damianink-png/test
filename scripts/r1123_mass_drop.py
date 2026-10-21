"""Native Qt drop zone: STEP files and Explorer folders."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame

class MassDropArea(QFrame):
    def __init__(self,add_callback,parent=None):
        super().__init__(parent)
        self._add_callback=add_callback
        self.setObjectName('mass-drop')
        self.setAcceptDrops(True)
        self.setProperty('dragActive',False)
    def _active(self,value):
        self.setProperty('dragActive',bool(value))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
    def _paths(self,event):
        mime=event.mimeData()
        return [url.toLocalFile() for url in mime.urls()
                if url.isLocalFile() and url.toLocalFile()] if mime.hasUrls() else []
    def dragEnterEvent(self,event):
        paths=self._paths(event)
        if paths:
            self._active(True)
            event.acceptProposedAction()
        else:
            event.ignore()
    def dragMoveEvent(self,event):
        if self._paths(event):event.acceptProposedAction()
        else:event.ignore()
    def dragLeaveEvent(self,event):
        self._active(False)
        event.accept()
    def dropEvent(self,event):
        self._active(False)
        paths=self._paths(event)
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        self._add_callback(paths)
