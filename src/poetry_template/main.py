import logging

import flet as ft

from poetry_template.db import DatabaseHandler

# ロギング設定
logging.basicConfig(level=logging.INFO)

MAX_CONTENT_LENGTH = 50


class DocumentsView:
    """
    ドキュメント一覧画面を管理するクラス
    """

    def __init__(self, parent: "DatabaseGUI"):
        self.parent = parent
        # ドキュメントテーブルの定義
        self.documents_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("タイトル")),
                ft.DataColumn(ft.Text("内容")),
                ft.DataColumn(ft.Text("作成日時")),
                ft.DataColumn(ft.Text("更新日時")),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            vertical_lines=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            sort_column_index=0,
            sort_ascending=True,
            heading_row_height=70,
            data_row_min_height=60,
        )

    def get_view(self, page: ft.Page) -> ft.View:
        """ドキュメント一覧画面のビューを返す"""
        return ft.View(
            "/documents",
            [
                ft.AppBar(
                    title=ft.Text("ドキュメント一覧"),
                    center_title=True,
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.REFRESH_ROUNDED,
                            tooltip="更新",
                            on_click=lambda e: self.parent.load_documents(),
                        ),
                        ft.PopupMenuButton(
                            items=[
                                ft.PopupMenuItem(text="DB接続設定", on_click=lambda e: page.go("/connect")),
                                ft.PopupMenuItem(text="SQLクエリ実行", on_click=lambda e: page.go("/query")),
                            ]
                        ),
                    ],
                ),
                ft.Container(
                    ft.Column(
                        [
                            ft.Container(
                                self.documents_table,
                                padding=20,
                                expand=True,
                            ),
                        ]
                    ),
                    padding=10,
                    expand=True,
                ),
                ft.FloatingActionButton(
                    icon=ft.Icons.ADD, on_click=self.parent.create_new_document, tooltip="新規ドキュメント作成"
                ),
                ft.Container(self.parent.status_text, padding=10),
            ],
            scroll=ft.ScrollMode.AUTO,
        )


class ConnectionView:
    """
    データベース接続画面を管理するクラス
    """

    def __init__(self, parent: "DatabaseGUI"):
        self.parent = parent
        # データベースタイプ選択スイッチ
        self.db_type_switch = ft.Switch(value=parent.is_postgres)

    def get_view(self, page: ft.Page) -> ft.View:
        """データベース接続画面のビューを返す"""
        return ft.View(
            "/connect",
            [
                ft.AppBar(title=ft.Text("データベース接続"), center_title=True),
                ft.Container(
                    ft.Column(
                        [
                            ft.Card(
                                content=ft.Container(
                                    ft.Column(
                                        [
                                            ft.Text("データベースタイプを選択", size=20, weight=ft.FontWeight.BOLD),
                                            ft.Row(
                                                [
                                                    ft.Text("SQLite", weight=ft.FontWeight.W_500),
                                                    self.db_type_switch,
                                                    ft.Text("PostgreSQL", weight=ft.FontWeight.W_500),
                                                ],
                                                alignment=ft.MainAxisAlignment.CENTER,
                                            ),
                                            ft.ElevatedButton(
                                                "接続",
                                                icon=ft.Icons.CONNECT_WITHOUT_CONTACT,
                                                on_click=self.parent.connect_to_database,
                                                width=200,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    padding=30,
                                    width=400,
                                ),
                                elevation=5,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                ),
                ft.Container(self.parent.status_text, padding=10),
            ],
        )


class QueryView:
    """
    SQLクエリ実行画面を管理するクラス
    """

    def __init__(self, parent: "DatabaseGUI"):
        self.parent = parent

        # SQLクエリエディタ
        self.sql_query_field = ft.TextField(
            label="SQLクエリを入力",
            multiline=True,
            min_lines=3,
            max_lines=8,
            hint_text="例: SELECT * FROM documents WHERE title LIKE '%検索語%'",
            expand=True,
        )

        # クエリ結果表示
        self.result_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("結果"))
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
        )

        self.query_result_text = ft.Text("クエリ実行結果がここに表示されます")

        self.sample_buttons = ft.Column(
            [
                ft.Text("サンプルクエリ"),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "全件検索",
                            on_click=lambda e: self.set_sample_query("SELECT * FROM documents"),
                        ),
                        ft.ElevatedButton(
                            "タイトル検索",
                            on_click=lambda e: self.set_sample_query(
                                "SELECT * FROM documents WHERE title LIKE '%検索語%'"
                            ),
                        ),
                    ],
                    wrap=True,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "新規追加",
                            on_click=lambda e: self.set_sample_query(
                                "INSERT INTO documents (title, content) VALUES ('新規タイトル', '新規内容')"
                            ),
                        ),
                        ft.ElevatedButton(
                            "更新",
                            on_click=lambda e: self.set_sample_query(
                                "UPDATE documents SET title = '更新タイトル', content = '更新内容' WHERE document_id = 1" # noqa
                            ),
                        ),
                        ft.ElevatedButton(
                            "削除",
                            on_click=lambda e: self.set_sample_query("DELETE FROM documents WHERE document_id = 1"),
                        ),
                    ]
                ),
            ],
        )

    def set_sample_query(self, query: str) -> None:
        """サンプルクエリをセットする"""
        self.sql_query_field.value = query
        self.parent.page.update()

    def get_view(self, page: ft.Page) -> ft.View:
        """SQLクエリ実行画面のビューを返す"""
        return ft.View(
            "/query",
            [
                ft.AppBar(
                    title=ft.Text("SQLクエリ実行"),
                    center_title=True,
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="ドキュメント一覧に戻る",
                            on_click=lambda e: page.go("/documents"),
                        ),
                    ],
                ),
                ft.Container(
                    ft.Column(
                        [
                            ft.Container(
                                ft.Column(
                                    [
                                        self.sample_buttons,
                                        ft.Divider(),
                                        self.sql_query_field,
                                        ft.ElevatedButton(
                                            "実行", icon=ft.Icons.PLAY_ARROW, on_click=self.execute_custom_query
                                        ),
                                        self.query_result_text,
                                        ft.Container(
                                            self.result_table,
                                            expand=True,
                                        ),
                                    ]
                                ),
                                padding=20,
                                expand=True,
                            ),
                        ]
                    ),
                    padding=10,
                    expand=True,
                ),
                ft.Container(self.parent.status_text, padding=10),
            ],
            scroll=ft.ScrollMode.AUTO,
        )

    def _refresh_result_table(self, results: list[tuple]) -> str:
        """クエリ結果のテーブルを更新する"""
        if len(results) > 0:
            # カラム名を取得（ここでは仮にインデックスを使用）
            columns = [f"列{i+1}" for i in range(len(results[0]))]
            self.result_table.columns = [ft.DataColumn(ft.Text(col)) for col in columns]

            self.result_table.rows = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(str(cell))) for cell in row]) for row in results
            ]
            result_str = f"{len(results)}行が選択されました"
        else:
            self.result_table.rows = []
            result_str = "0行が選択されました"

        return result_str


    def execute_custom_query(self, e: ft.ControlEvent) -> None:
        """SQLクエリを実行し結果を表示する"""
        page: ft.Page = self.parent.page
        try:
            query = self.sql_query_field.value.strip()
            logging.info(f"Executing query: {query}")
            if query == "":
                self.query_result_text.value = "クエリを入力してください"
                page.update()
                return

            is_select = query.upper().startswith("SELECT")

            if is_select:
                results = self.parent.db_handler.fetch_query(query)

                # 結果表示用のテーブル作成
                # if results and len(results) > 0:
                #     # カラム名を取得（ここでは仮にインデックスを使用）
                #     columns = [f"列{i+1}" for i in range(len(results[0]))]

                #     self.result_table.columns = [ft.DataColumn(ft.Text(col)) for col in columns]

                #     self.result_table.rows = [
                #         ft.DataRow(cells=[ft.DataCell(ft.Text(str(cell))) for cell in row]) for row in results
                #     ]

                #     self.query_result_text.value = f"{len(results)}行が選択されました"
                # else:
                #     self.result_table.rows = []
                #     self.query_result_text.value = "0行が選択されました"
                if results:
                    res = self._refresh_result_table(results)
                    self.query_result_text.value = res
                else:
                    self.result_table.rows = []
                    self.query_result_text.value = "0行が選択されました"
            else:
                self.parent.db_handler.execute_query(query)
                self.query_result_text.value = "クエリが実行されました"
                results = self.parent.db_handler.fetch_query("SELECT * FROM documents")
                if results:
                    self._refresh_result_table(results)
                else:
                    self.result_table.rows = []

        except Exception as err:
            self.query_result_text.value = f"エラー: {str(err)}"
            self.result_table.rows = []

        page.update()


class DialogManager:
    """
    ダイアログ関連の操作を管理するクラス
    """

    def __init__(self, parent: "DatabaseGUI"):
        self.parent = parent

    def show_document_detail(self, doc_id: int) -> None:
        """ドキュメント詳細ダイアログを表示する"""
        page = self.parent.page
        document = None
        for doc in self.parent.current_documents:
            if doc[0] == doc_id:
                document = doc
                break

        if not document:
            logging.warning(f"Document not found: {doc_id}")
            return

        edit_title_field = ft.TextField(label="タイトル", value=document[1])
        edit_content_field = ft.TextField(label="内容", multiline=True, min_lines=5, max_lines=15, value=document[2])

        detail_dialog: ft.AlertDialog = ft.AlertDialog(
            title=ft.Text(f"ドキュメント ID: {doc_id}"),
            content=ft.Column(
                [
                    edit_title_field,
                    edit_content_field,
                    ft.Row(
                        [
                            ft.Text(f"作成日: {document[3]}"),
                            ft.Text(f"更新日: {document[4]}"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                tight=True,
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("閉じる", on_click=lambda e: page.close(detail_dialog)),
                ft.OutlinedButton(
                    "削除", on_click=lambda e: self._delete_document(e, doc_id, detail_dialog), icon=ft.Icons.DELETE
                ),
                ft.ElevatedButton(
                    "更新",
                    on_click=lambda e: self._update_document(
                        e, doc_id, detail_dialog, edit_title_field, edit_content_field
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(detail_dialog)
        page.update()

    def _update_document(
        self,
        e: ft.ControlEvent,
        doc_id: int,
        dialog: ft.AlertDialog,
        title_field: ft.TextField,
        content_field: ft.TextField,
    ) -> None:
        """ドキュメントを更新する"""
        page = self.parent.page
        try:
            title = title_field.value
            content = content_field.value

            self.parent.db_handler.execute_query(
                "UPDATE documents SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP WHERE document_id = %s",
                (title, content, doc_id),
            )
            page.snack_bar = ft.SnackBar(ft.Text("ドキュメントを更新しました"))
            page.snack_bar.open = True
            page.close(dialog)
            self.parent.load_documents()
        except Exception as err:
            page.snack_bar = ft.SnackBar(ft.Text(f"エラー: {str(err)}"))
            page.snack_bar.open = True
        page.update()

    def _delete_document(self, e: ft.ControlEvent, doc_id: int, parent_dialog: ft.AlertDialog) -> None:
        """ドキュメント削除時の確認ダイアログを表示する"""
        page = self.parent.page

        def confirm_delete(e: ft.ControlEvent) -> None:
            try:
                self.parent.db_handler.execute_query("DELETE FROM documents WHERE document_id = %s", (doc_id,))
                page.snack_bar = ft.SnackBar(ft.Text("ドキュメントを削除しました"))
                page.snack_bar.open = True
                page.close(confirm_dialog)
                parent_dialog.open = False
                self.parent.load_documents()
            except Exception as err:
                page.snack_bar = ft.SnackBar(ft.Text(f"エラー: {str(err)}"))
                page.snack_bar.open = True
            page.update()

        confirm_dialog: ft.AlertDialog = ft.AlertDialog(
            title=ft.Text("削除の確認"),
            content=ft.Text(f"ID: {doc_id} のドキュメントを削除しますか？"),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda e: page.close(confirm_dialog)),
                ft.ElevatedButton("削除", on_click=confirm_delete, color="error"),
            ],
        )
        page.open(confirm_dialog)
        page.update()

    def show_new_document_dialog(self) -> None:
        """新規ドキュメント作成ダイアログを表示する"""
        page = self.parent.page

        new_title_field = ft.TextField(label="タイトル", autofocus=True)
        new_content_field = ft.TextField(label="内容", multiline=True, min_lines=3, max_lines=10)

        new_doc_dialog: ft.AlertDialog = ft.AlertDialog(
            title=ft.Text("新規ドキュメント"),
            content=ft.Column([new_title_field, new_content_field], tight=True, spacing=20),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda e: page.close(new_doc_dialog)),
                ft.ElevatedButton(
                    "保存",
                    on_click=lambda e: self._save_new_document(e, new_doc_dialog, new_title_field, new_content_field),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(new_doc_dialog)
        page.update()

    def _save_new_document(
        self, e: ft.ControlEvent, dialog: ft.AlertDialog, title_field: ft.TextField, content_field: ft.TextField
    ) -> None:
        """新規ドキュメントを保存する"""
        page = self.parent.page
        try:
            title = title_field.value
            content = content_field.value
            if not title:
                page.snack_bar = ft.SnackBar(ft.Text("タイトルを入力してください"))
                page.snack_bar.open = True
                page.update()
                return

            self.parent.db_handler.execute_query(
                "INSERT INTO documents (title, content) VALUES (%s, %s)", (title, content)
            )
            page.snack_bar = ft.SnackBar(ft.Text("ドキュメントを作成しました"))
            page.snack_bar.open = True
            page.close(dialog)
            self.parent.load_documents()
        except Exception as err:
            page.snack_bar = ft.SnackBar(ft.Text(f"エラー: {str(err)}"))
            page.snack_bar.open = True
        page.update()


class DatabaseGUI:
    """
    データベース操作用GUIアプリケーションのメインクラス
    """

    def __init__(self) -> None:
        # データベース関連の初期化
        self.db_handler = DatabaseHandler()
        self.current_documents: list[tuple] = []
        self.is_postgres = False  # デフォルトDB

        # 内部状態
        self.page: ft.Page = None
        self.status_text = ft.Text("準備完了", size=12)

        # 各画面を管理するクラスの初期化
        self.connection_view = ConnectionView(self)
        self.documents_view = DocumentsView(self)
        self.query_view = QueryView(self)
        self.dialog_manager = DialogManager(self)

    def main(self, page: ft.Page) -> None:
        """
        アプリケーションのエントリーポイント
        """
        # アプリの基本設定
        self.page = page
        page.title = "Study SQL"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.padding = 0

        # ルーティング
        def route_change(e: ft.ControlEvent) -> None:
            """画面遷移を処理するコールバック関数"""
            page.views.clear()

            if page.route == "/connect":
                page.views.append(self.connection_view.get_view(page))
            elif page.route == "/documents":
                page.views.append(self.documents_view.get_view(page))
            elif page.route == "/query":
                page.views.append(self.query_view.get_view(page))
            else:
                page.views.append(self.connection_view.get_view(page))

            page.update()

        page.on_route_change = route_change
        page.go("/connect")

    def load_documents(self) -> None:
        """ドキュメント一覧をデータベースから読み込む"""

        def truncate_text(text: str, length: int = 50) -> str:
            text_safe = text or ""
            return text_safe[:length] + "..." if len(text) > length else text_safe

        try:
            if self.db_handler.is_connected():
                self.current_documents = self.db_handler.fetch_query("SELECT * FROM documents")
                self.documents_view.documents_table.rows.clear()
                for doc in self.current_documents:
                    self.documents_view.documents_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(doc[0]))),  # ID
                                ft.DataCell(ft.Text(truncate_text(doc[1], MAX_CONTENT_LENGTH))),  # Title
                                ft.DataCell(ft.Text(truncate_text(doc[2], MAX_CONTENT_LENGTH))),  # Content
                                ft.DataCell(ft.Text(str(doc[3]))),  # Created
                                ft.DataCell(ft.Text(str(doc[4]))),  # Updated
                            ],
                            on_select_changed=lambda e, doc_id=doc[0]: self.dialog_manager.show_document_detail(doc_id),
                        )
                    )
                self.status_text.value = f"{len(self.current_documents)} ドキュメントが読み込まれました"
            else:
                self.status_text.value = "データベースに接続されていません"
        except Exception as err:
            self.status_text.value = f"エラー: {str(err)}"
        self.page.update()

    def connect_to_database(self, e: ft.ControlEvent) -> None:
        """データベースに接続する"""
        try:
            if self.db_handler.is_connected():
                self.db_handler.close_connection()

            self.is_postgres = self.connection_view.db_type_switch.value
            self.db_handler = DatabaseHandler.connect(use_postgres=self.is_postgres)
            self.status_text.value = f"{'PostgreSQL' if self.is_postgres else 'SQLite'} に接続しました"
            self.load_documents()

            # 接続後はメインコンテンツを表示
            self.page.go("/documents")
        except Exception as err:
            self.status_text.value = f"接続エラー: {str(err)}"
            self.page.update()

    def create_new_document(self, e: ft.ControlEvent) -> None:
        """新規ドキュメント作成ダイアログを表示する"""
        self.dialog_manager.show_new_document_dialog()


# アプリ起動
def main() -> None:
    """アプリケーションのエントリーポイント関数"""
    ft.app(target=lambda page: DatabaseGUI().main(page))


if __name__ == "__main__":
    main()
