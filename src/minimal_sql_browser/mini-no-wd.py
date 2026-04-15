import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QTextEdit, QTableView, QComboBox,
                             QLabel, QSplitter, QSizePolicy, QFileDialog, QAction)
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlQueryModel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

class MiniSqlApp(QWidget):
    focus_in = pyqtSignal(object)

    def __init__(self, db_path):
        super().__init__()
        self.setWindowTitle(f"SQLite Viewer - {db_path}")

        # Global Font 12pt
        self.setFont(QFont("Segoe UI", 18))

        if db_path is not None:
            self.db = QSqlDatabase.addDatabase("QSQLITE")
            self.db.setDatabaseName(db_path)

            if not self.db.open(): print(f"DB Error: {db_path}")

        main_splitter = QSplitter(Qt.Vertical)
        
        # --- TOP: EDITOR & ERRORS ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
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
        top_layout.addWidget(QLabel("Operation Info / Errors:"))
        top_layout.addWidget(self.info_output)
        main_splitter.addWidget(top_widget)

        # --- BOTTOM: TABLES ---
        table_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Result
        res_w = QWidget(); res_l = QVBoxLayout(res_w)
        self.query_view = QTableView()
        self.query_model = QSqlQueryModel()
        self.query_view.setModel(self.query_model)
        res_l.addWidget(QLabel("Query Result:")); res_l.addWidget(self.query_view)
        table_splitter.addWidget(res_w)

        # Right: Watcher
        wat_w = QWidget(); wat_l = QVBoxLayout(wat_w)
        self.table_selector = QComboBox()
        self.table_selector.currentTextChanged.connect(self.refresh_full_view)
        self.full_view = QTableView()
        self.full_model = QSqlQueryModel()
        self.full_view.setModel(self.full_model)
        wat_l.addWidget(QLabel("Table Watcher:"));
        wat_l.addWidget(self.table_selector);
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
            
            self.info_output.setText(msg + "\n" + self.info_output.toPlainText())
            self.info_output.setStyleSheet("background: #fdfdfd; color: #2e7d32;") # Green for success
            self.refresh_table_list()
            self.refresh_full_view()
        else:
            self.info_output.setText(query.lastError().text()  + "\n" + self.info_output.toPlainText())
            self.info_output.setStyleSheet("background: #fdfdfd; color: #d32f2f;") # Red for error

    def refresh_table_list(self):
        current = self.table_selector.currentText()
        self.table_selector.blockSignals(True)
        self.table_selector.clear()
        self.table_selector.addItems(self.db.tables())
        if current in self.db.tables(): self.table_selector.setCurrentText(current)
        self.table_selector.blockSignals(False)

    def refresh_full_view(self):
        table = self.table_selector.currentText()
        if table: self.full_model.setQuery(f"SELECT * FROM {table}")

    def open_database(self, db_path):
        # Close current DB connection
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
        self.query_model.clear()
        self.full_model.clear()
        self.info_output.setText(f"Opened: {db_path}\n" + self.info_output.toPlainText())
        self.info_output.setStyleSheet("background: #fdfdfd; color: #2e7d32;")
        QTimer.singleShot(50, self.refresh_full_view)

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