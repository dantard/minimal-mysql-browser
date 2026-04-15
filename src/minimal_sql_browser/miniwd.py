import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QTextEdit, QTableView, QComboBox,
                             QLabel, QSplitter, QSizePolicy, QFileDialog, QAction, QShortcut)
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlQueryModel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os


class DbChangeHandler(FileSystemEventHandler):
    """Watchdog handler that emits a Qt signal when the watched DB file is modified."""

    def __init__(self, db_path, signal):
        super().__init__()
        self._db_path = os.path.abspath(db_path)
        self._signal = signal

    def on_modified(self, event):
        if not event.is_directory and os.path.abspath(event.src_path) == self._db_path:
            self._signal.emit()


class MiniSqlApp(QWidget):
    focus_in = pyqtSignal(object)
    _db_changed = pyqtSignal()  # internal signal, fired from watchdog thread

    def __init__(self, db_path):
        super().__init__()
        self.counter = 0
        self.setWindowTitle(f"SQLite Viewer - {db_path}")

        # Global Font 12pt
        #self.setFont(QFont("Segoe UI", 18))

        self._observer = None  # watchdog Observer instance

        if db_path is not None:
            self.db = QSqlDatabase.addDatabase("QSQLITE")
            self.db.setDatabaseName(db_path)

            if not self.db.open(): print(f"DB Error: {db_path}")

        main_splitter = QSplitter(Qt.Vertical)

        # --- TOP: EDITOR & ERRORS ---
        self.top_widget = QWidget()
        top_layout = QVBoxLayout(self.top_widget)

        qlbl = QLabel("Query Editor (Ctrl+Enter):")
        qlbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)



        self.query_input = QTextEdit()
        self.query_input.setMinimumHeight(150)

        self.info_output = QTextEdit()
        self.info_output.setReadOnly(True)
        self.info_output.setMinimumHeight(120)
        self.info_output.setStyleSheet("background: #fdfdfd; color: #333;")

        top_layout.addWidget(qlbl)
        top_layout.addWidget(self.query_input)
        op_info = QLabel("Operation Info / Errors:")
        top_layout.addWidget(op_info)
        top_layout.addWidget(self.info_output)
        main_splitter.addWidget(self.top_widget)

        # --- BOTTOM: TABLES ---
        table_splitter = QSplitter(Qt.Horizontal)

        # Left: Result
        self.res_w = QWidget()
        res_l = QVBoxLayout(self.res_w)
        self.query_view = QTableView()
        self.query_model = QSqlQueryModel()
        self.query_view.setModel(self.query_model)
        query_res = QLabel("Query Result:")
        res_l.addWidget(query_res)
        res_l.addWidget(self.query_view)
        table_splitter.addWidget(self.res_w)

        # Right: Watcher
        wat_w = QWidget()
        wat_l = QVBoxLayout(wat_w)
        self.table_selector = QComboBox()
        self.table_selector.currentTextChanged.connect(self.refresh_full_view)
        self.full_view = QTableView()
        self.full_model = QSqlQueryModel()
        self.full_view.setModel(self.full_model)
        table_w_lbl = QLabel("Table Watcher:")
        wat_l.addWidget(table_w_lbl)
        wat_l.addWidget(self.table_selector)
        wat_l.addWidget(self.full_view)
        table_splitter.addWidget(wat_w)

        main_splitter.addWidget(table_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)

        #self.setCentralWidget(main_splitter)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_splitter)
        self.refresh_table_list()
        self.refresh_full_view()

        # Connect the internal signal (emitted from watchdog thread) to refresh,
        # ensuring the slot always runs on the Qt main thread.
        self._db_changed.connect(self.refresh_full_view)

        # Start watching the initial DB file
        if db_path is not None:
            self._start_watching(db_path)

        q = QShortcut("Ctrl+B", self)
        q.activated.connect(self.loop_views)

        self.fontable = [qlbl, self.query_input, self.info_output,
                         self.table_selector, self.full_view,
                         self.query_view, op_info, query_res, table_w_lbl]

        self.set_font_size(18)

    def loop_views(self):
        self.res_w.setVisible(not self.res_w.isVisible())
        self.top_widget.setVisible(not self.top_widget.isVisible())


    # ------------------------------------------------------------------
    # Watchdog helpers
    # ------------------------------------------------------------------

    def _start_watching(self, db_path):
        """Start a watchdog Observer for the given DB file."""
        self._stop_watching()
        abs_path = os.path.abspath(db_path)
        watch_dir = os.path.dirname(abs_path) or "."
        handler = DbChangeHandler(abs_path, self._db_changed)
        self._observer = Observer()
        self._observer.schedule(handler, watch_dir, recursive=False)
        self._observer.start()

    def _stop_watching(self):
        """Stop and join any running watchdog Observer."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def closeEvent(self, event):
        self._stop_watching()
        super().closeEvent(event)

    # ------------------------------------------------------------------

    def open_database_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open SQLite Database", "", "SQLite DB Files (*.db *.sqlite *.sqlite3);;All Files (*)")
        if path:
            self.open_database(path)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() == Qt.ControlModifier:
            self.run_query()
        else:
            super().keyPressEvent(event)

    def run_query(self):
        self.counter = self.counter + 1
        sql = self.query_input.toPlainText()
        query = QSqlQuery()
        if query.exec_(sql):
            self.query_model.setQuery(query)

            # Check rows affected or returned
            affected = query.numRowsAffected()
            if affected > 0:
                msg = f"Success. Rows affected: {affected}"
            else:
                # If it's a SELECT, count rows in the model
                msg = f"Success. Rows returned: {self.query_model.rowCount()}"

            msg = f"[{self.counter}] " + msg

            self.info_output.setText(msg + "\n" + self.info_output.toPlainText())
            self.info_output.setStyleSheet("background: #fdfdfd; color: #2e7d32;") # Green for success
            self.refresh_table_list()
            #self.refresh_full_view()
        else:
            self.info_output.setText(f"[{self.counter}] " + query.lastError().text()  + "\n" + self.info_output.toPlainText())
            self.info_output.setStyleSheet("background: #fdfdfd; color: #d32f2f;") # Red for error

    def refresh_table_list(self):
        current = self.table_selector.currentText()
        self.table_selector.blockSignals(True)
        self.table_selector.clear()
        self.table_selector.addItems(self.db.tables())
        if current in self.db.tables():
            self.table_selector.setCurrentText(current)
        self.table_selector.blockSignals(False)
        self.query_view.resizeColumnsToContents()

    def refresh_full_view(self):
        table = self.table_selector.currentText()
        if table:
            self.full_model.setQuery(f"SELECT * FROM {table}")
            self.full_view.resizeColumnsToContents()

    def open_database(self, db_path):
        self._stop_watching()

        # Clear models FIRST, before closing/removing the connection
        self.query_model.clear()
        self.full_model.clear()

        self.db.close()
        QSqlDatabase.removeDatabase(self.db.connectionName())

        # Open new DB
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(db_path)
        if not self.db.open():
            self.info_output.setText(f"Failed to open: {db_path}\n" + self.info_output.toPlainText())
            self.info_output.setStyleSheet("background: #fdfdfd; color: #d32f2f;")
            return
        self.setWindowTitle(f"SQLite Viewer - {db_path}")
        self.refresh_table_list()
        self.info_output.setText(f"Opened: {db_path}\n" + self.info_output.toPlainText())
        self.info_output.setStyleSheet("background: #fdfdfd; color: #2e7d32;")
        QTimer.singleShot(50, self.refresh_full_view)
        self._start_watching(db_path)

    def set_dark_mode(self, enabled):
        if enabled:
            self.setStyleSheet("""
                QWidget { background: #2b2b2b; color: #f0f0f0; }
                QTableView { background: #3c3c3c; }
                QTextEdit { background: #3c3c3c; }
                QComboBox { background: #3c3c3c; }
            """)
        else:
            self.setStyleSheet("")

    def update_config(self):
        pass

    def is_selectable(self):
        return False

    def on_disk(self):
        return False

    def set_font_size(self, font_size):
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(font_size)
        for f in self.fontable:
            f.setFont(font)
        self.query_view.resizeColumnsToContents()
        self.full_view.resizeColumnsToContents()

    def get_font_size(self):
        return self.fontable[0].font().pixelSize() if self.fontable else 12

class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.mini_app = MiniSqlApp(db)
        self.setCentralWidget(self.mini_app)

        # Menu
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Database...", self)
        open_action.triggered.connect(self.mini_app.open_database_dialog)
        file_menu.addAction(open_action)

        self.setCentralWidget(self.mini_app)

def main():
    target_db = sys.argv[1] if len(sys.argv) > 1 else "data.db"
    app = QApplication(sys.argv)
    window = MainWindow(target_db)
    window.resize(1200, 900)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()