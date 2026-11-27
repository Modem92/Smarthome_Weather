"""Explicit Qt controls for manually requested design transfers."""
from wetterstation.designer.transfer import Transfer, result_message

from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QHBoxLayout,QMessageBox


class TransferWorker(QThread):
    progress=Signal(str);done=Signal(object);failed=Signal(str)
    def __init__(self,transfer,send,parent=None):super().__init__(parent);self.transfer=transfer;self.send=send
    def run(self):
        try:
            if self.send in ('timeline-enable','timeline-disable'):
                self.transfer.call(self.send,'--revision',self.transfer.result['current']['revision']);result=self.transfer.inspect()
            elif self.send=='restore':
                value=self.transfer.inspect();self.transfer.call('restore','--token',self.transfer.token,'--revision',value['current']['revision']);result=self.transfer.inspect()
            elif self.send=='new':result=self.transfer.start_new()
            else:result=self.transfer.send(self.progress.emit) if self.send else self.transfer.inspect()
            self.done.emit(result)
        except ValueError as exc:self.failed.emit(str(exc))
        except Exception:self.failed.emit('Verbindung oder Übernahme nicht bestätigt. Über „Stand prüfen“ erst den tatsächlichen Pi-Stand feststellen. Bei altem Programmstand zuerst den manuellen Updater verwenden.')


class TransferDialog(QDialog):
    def __init__(self,document,store,parent=None):
        super().__init__(parent);self.setWindowTitle('Gestaltung an Pi übertragen');self.resize(560,300);self.worker=None;self.transfer=None
        layout=QVBoxLayout(self);display=document['display'];layout.addWidget(QLabel(f"Entwurf: {display['width']} × {display['height']} · {len(document['pages'])} Seiten · {len(document['assets'])} Dateien"))
        self.status=QLabel('Vorhandene SSH-Verbindung verwenden. Die bisherige Pi-Gestaltung wird vor dem Ersetzen gesichert.');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();self.check=QPushButton('Stand prüfen');self.send=QPushButton('Jetzt übertragen');self.send.setEnabled(False);self.close_button=QPushButton('Schließen');row.addWidget(self.check);row.addWidget(self.send);row.addWidget(self.close_button);layout.addLayout(row)
        self.check.clicked.connect(lambda:self.start(False));self.send.clicked.connect(lambda:self.start(True));self.close_button.clicked.connect(self.accept)
        self.restore_button=QPushButton('Vorherige Gestaltung wiederherstellen');self.restore_button.setEnabled(False);layout.addWidget(self.restore_button);self.restore_button.clicked.connect(lambda:self.start('restore'))
        self.new_button=QPushButton('Neue Übertragung vorbereiten');self.new_button.setEnabled(False);self.new_button.setToolTip('Offenen Vorgang sicher beenden und den aktuellen Pi-Stand neu prüfen. Die Anzeige bleibt dabei erhalten.');layout.addWidget(self.new_button);self.new_button.clicked.connect(lambda:self.start('new'))
        timeline_row=QHBoxLayout();self.timeline_enable=QPushButton('Zusatzabrufe am Pi aktivieren …');self.timeline_disable=QPushButton('Zusatzabrufe am Pi ausschalten')
        for button in (self.timeline_enable,self.timeline_disable):button.setEnabled(False);timeline_row.addWidget(button)
        layout.addLayout(timeline_row)
        self.timeline_enable.clicked.connect(self.enable_timelines);self.timeline_disable.clicked.connect(lambda:self.start('timeline-disable'))
        try:self.transfer=Transfer(document,store)
        except ValueError as exc:self.status.setText(str(exc));self.check.setEnabled(False)
        except Exception:self.status.setText('SSH-Einrichtung fehlt oder ist nicht lesbar. Zuerst „Set up SSH once.cmd“ verwenden.');self.check.setEnabled(False)

    def start(self,send):
        if not self.transfer:return
        self.check.setEnabled(False);self.send.setEnabled(False);self.close_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.new_button.setEnabled(False)
        self.timeline_enable.setEnabled(False);self.timeline_disable.setEnabled(False)
        self.worker=TransferWorker(self.transfer,send,self);self.worker.progress.connect(self.status.setText);self.worker.done.connect(self.finished);self.worker.failed.connect(self.failure);self.worker.start()

    def finished(self,value):
        self.status.setText(result_message(value));self.check.setEnabled(True);self.close_button.setEnabled(True)
        state=value.get('transaction',{}).get('state')
        resumable=state in ('prepared','staged') and value['current']['revision']==value['transaction'].get('expected_revision')
        self.send.setEnabled(not self.transfer.token or resumable or state=='restored')
        self.send.setText('Übertragung fortsetzen' if resumable else 'Erneut übertragen' if state=='restored' else 'Jetzt übertragen')
        self.restore_button.setEnabled(value.get('transaction',{}).get('state')=='applied' and bool(value['transaction'].get('backup')))
        self.new_button.setEnabled(bool(self.transfer.token))
        timelines=value['current'].get('timelines',{})
        supported=timelines.get('design_supported',False)
        self.timeline_enable.setEnabled(supported and timelines.get('estimate',{}).get('fits',False))
        self.timeline_disable.setEnabled(bool(timelines))
        from wetterstation.designer.activation import STATE_TEXT
        self.status.setText(self.status.text()+'\nPi: '+STATE_TEXT.get(timelines.get('state'),'Zeitreihenfreigabe unbekannt'))

    def enable_timelines(self):
        if not self.transfer or not self.transfer.result:return
        estimate=self.transfer.result['current'].get('timelines',{}).get('estimate',{})
        details='\n'.join(f"{s['source']}: alle {s['refresh']} Minuten, bis zu {s['calls']} Zusatzanfragen/Tag" for s in estimate.get('sources',[]))
        reply=QMessageBox.question(self,'Zusatzabrufe am Pi aktivieren?',details+
            f"\n\nGeprüfte aktive Pi-Gestaltung: {estimate.get('total','?')}/1000 Anfragen pro Tag einschließlich Reserve.\n"
            'Erst die nächste reguläre Live-Aktualisierung ruft Zusatzdaten ab. Eine geschlossene Anwendung bleibt geschlossen.',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if reply==QMessageBox.StandardButton.Yes:self.start('timeline-enable')

    def failure(self,message):self.status.setText(message);self.check.setEnabled(True);self.close_button.setEnabled(True);self.send.setEnabled(False)

    def reject(self):
        if self.worker and self.worker.isRunning():return
        super().reject()
