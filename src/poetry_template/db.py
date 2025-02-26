import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar, cast

import psycopg2
import psycopg2.pool

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="DatabaseHandler")


class BaseDatabaseHandler(ABC):
    """
    データベース操作のベースクラス。
    個別のデータベースクラスはこれを継承して実装する。
    すべてのデータベース実装はこのインターフェースに従う必要がある。
    """

    @abstractmethod
    def connect(self) -> None:
        """データベースに接続するための初期化処理"""
        raise NotImplementedError("子クラスで実装する必要があります")

    @abstractmethod
    def is_connected(self) -> bool:
        """
        データベース接続が確立されているかどうかを返す

        Returns:
            bool: 接続が有効な場合はTrue、それ以外はFalse
        """
        raise NotImplementedError("子クラスで実装する必要があります")

    @abstractmethod
    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        """
        データを挿入、更新、削除するクエリを実行

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ（プリペアドステートメント用）
        """
        raise NotImplementedError("子クラスで実装する必要があります")

    @abstractmethod
    def fetch_query(self, query: str, params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
        """
        データを取得するクエリを実行

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ（プリペアドステートメント用）

        Returns:
            List[Tuple[Any, ...]]: クエリ結果の行のリスト
        """
        raise NotImplementedError("子クラスで実装する必要があります")

    @abstractmethod
    def close_connection(self) -> None:
        """データベース接続を閉じる"""
        raise NotImplementedError("子クラスで実装する必要があります")


class SQLiteDatabaseHandler(BaseDatabaseHandler):
    """SQLiteデータベースを操作するためのハンドラー"""

    def __init__(self, database_path: str, init_sql_path: str | None = None) -> None:
        """
        SQLiteDatabaseHandlerを初期化する

        Args:
            database_path: SQLiteデータベースファイルのパス
            init_sql_path: 初期化SQLスクリプトのパス（オプション）
        """
        self.connection: sqlite3.Connection | None = None
        self.database_path = self.get_db_path(database_path)
        self.init_sql_path = init_sql_path
        self.connect()

    def get_db_path(self, db_path: str) -> str:
        """
        相対パスから絶対パスを生成する

        Args:
            db_path: データベースの相対パス

        Returns:
            str: データベースファイルの絶対パス
        """
        app_dir = Path(__file__).resolve().parent.parent.parent
        full_path = str(app_dir) + db_path
        return full_path

    def connect(self) -> None:
        """
        SQLiteデータベースに接続する
        データベースが存在しない場合は作成する
        """
        try:
            if not Path(self.database_path).exists():
                self._create_database()
            self.connection = sqlite3.connect(self.database_path, check_same_thread=False)
            logger.info("SQLite connection initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"SQLite connection failed: {e}")
            raise

    def is_connected(self) -> bool:
        """
        SQLite接続が確立されているかどうかを返す

        Returns:
            bool: 接続が有効な場合はTrue、それ以外はFalse
        """
        return self.connection is not None

    def _create_database(self) -> None:
        """
        SQLiteデータベースを作成し初期化する
        データベースディレクトリが存在しない場合は作成する
        """
        # データベースファイルのディレクトリを作成
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

        if self.init_sql_path:
            try:
                with sqlite3.connect(self.database_path) as connection:
                    with open(self.init_sql_path, encoding="utf-8") as f:
                        connection.executescript(f.read())
                logger.info("SQLite database created with initial schema.")
            except (OSError, sqlite3.Error) as e:
                logger.error(f"Failed to initialize database: {e}")
                raise
        else:
            logger.warning("No initial schema file specified. Creating empty database.")

    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        """
        クエリを実行（データ挿入、更新、削除）

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ
        """
        if not self.connection:
            raise RuntimeError("Database connection is not established")

        # SQLite形式に変換（%s -> ?）
        query = query.replace("%s", "?")

        try:
            with self.connection:
                cursor = self.connection.cursor()
                cursor.execute(query, params or [])
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def fetch_query(self, query: str, params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
        """
        クエリを実行して結果を取得

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ

        Returns:
            List[Tuple[Any, ...]]: クエリ結果の行のリスト
        """
        if not self.connection:
            raise RuntimeError("Database connection is not established")

        # SQLite形式に変換（%s -> ?）
        query = query.replace("%s", "?")

        try:
            with self.connection:
                cursor = self.connection.cursor()
                cursor.execute(query, params or [])
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def close_connection(self) -> None:
        """SQLite接続を閉じる"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("SQLite connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Failed to close SQLite connection: {e}")


class PostgreSQLDatabaseHandler(BaseDatabaseHandler):
    """PostgreSQLデータベースを操作するためのハンドラー"""

    def __init__(self, conninfo: str) -> None:
        """
        PostgreSQLDatabaseHandlerを初期化する

        Args:
            conninfo: PostgreSQL接続情報文字列
        """
        self.conninfo = conninfo
        self.pool: psycopg2.pool.SimpleConnectionPool | None = None
        self.connect()

    def connect(self) -> None:
        """PostgreSQLデータベースに接続する"""
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(minconn=1, maxconn=20, dsn=self.conninfo)
            if not self.pool:
                raise psycopg2.DatabaseError("Failed to create connection pool")
            logger.info("PostgreSQL connection pool initialized.")
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise

    def is_connected(self) -> bool:
        """
        PostgreSQL接続が確立されているかどうかを返す

        Returns:
            bool: 接続が有効な場合はTrue、それ以外はFalse
        """
        return self.pool is not None

    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        """
        クエリを実行（データ挿入、更新、削除）

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ
        """
        if not self.pool:
            raise RuntimeError("Database connection pool is not established")

        conn = None
        try:
            conn = self.pool.getconn()
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if conn and self.pool:
                self.pool.putconn(conn)

    def fetch_query(self, query: str, params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
        """
        クエリを実行して結果を取得

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ

        Returns:
            List[Tuple[Any, ...]]: クエリ結果の行のリスト
        """
        if not self.pool:
            raise RuntimeError("Database connection pool is not established")

        conn = None
        try:
            conn = self.pool.getconn()
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cast(list[tuple[Any, ...]], cursor.fetchall())
        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if conn and self.pool:
                self.pool.putconn(conn)

    def close_connection(self) -> None:
        """PostgreSQL接続を閉じる"""
        if self.pool:
            try:
                self.pool.closeall()
                self.pool = None
                logger.info("PostgreSQL connection pool closed.")
            except psycopg2.Error as e:
                logger.error(f"Failed to close PostgreSQL connection pool: {e}")


class DatabaseHandler:
    """
    データベースハンドラの統合インターフェース
    SQLiteとPostgreSQLの切り替えを提供する
    """

    def __init__(self, use_postgres: bool = False) -> None:
        """
        DatabaseHandlerを初期化する

        Args:
            use_postgres: PostgreSQLを使用する場合はTrue、SQLiteを使用する場合はFalse
        """
        self.use_postgres = use_postgres
        self.handler: BaseDatabaseHandler | None = None

    @classmethod
    def connect(cls: type[T], use_postgres: bool = False) -> T:
        """
        データベースに接続する

        Args:
            use_postgres: PostgreSQLを使用する場合はTrue、SQLiteを使用する場合はFalse

        Returns:
            DatabaseHandler: 接続されたDatabaseHandlerインスタンス
        """
        instance = cls(use_postgres)
        instance._connect(use_postgres)
        return instance

    def _connect(self, use_postgres: bool | None = None) -> None:
        """
        データベース接続を初期化する

        Args:
            use_postgres: PostgreSQLを使用する場合はTrue、SQLiteを使用する場合はFalse
        """
        if use_postgres is not None:
            self.use_postgres = use_postgres

        if self.use_postgres:
            conninfo = (
                f"postgresql://{os.environ['POSTGRES_USER']}:"
                f"{os.environ['POSTGRES_PASSWORD']}@"
                f"{os.environ['POSTGRES_HOST']}:"
                f"{os.environ['POSTGRES_PORT']}/"
                f"{os.environ['POSTGRES_DB_NAME']}?sslmode=disable"
            )
            self.handler = PostgreSQLDatabaseHandler(conninfo)
        else:
            database_path = os.environ["SQLITE_DB_PATH"]
            init_sql_path = "db/sqlite/init/1_init.sql"
            self.handler = SQLiteDatabaseHandler(database_path, init_sql_path)

    def reconnect(self, use_postgres: bool = False) -> None:
        """
        データベース接続を再接続する

        Args:
            use_postgres: PostgreSQLを使用する場合はTrue、SQLiteを使用する場合はFalse
        """
        self.close_connection()
        self._connect(use_postgres)

    def is_connected(self) -> bool:
        """
        データベース接続が確立されているかどうかを返す

        Returns:
            bool: 接続が有効な場合はTrue、それ以外はFalse
        """
        if not self.handler:
            return False
        return self.handler.is_connected()

    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        """
        クエリを実行（データ挿入、更新、削除）

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ
        """
        if not self.handler:
            raise RuntimeError("Database handler is not initialized")
        self.handler.execute_query(query, params)

    def fetch_query(self, query: str, params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
        """
        クエリを実行して結果を取得

        Args:
            query: 実行するSQLクエリ
            params: クエリパラメータ

        Returns:
            List[Tuple[Any, ...]]: クエリ結果の行のリスト
        """
        if not self.handler:
            raise RuntimeError("Database handler is not initialized")
        return self.handler.fetch_query(query, params)

    def close_connection(self) -> None:
        """データベース接続を閉じる"""
        if self.handler:
            self.handler.close_connection()


if __name__ == "__main__":
    db = DatabaseHandler.connect(use_postgres=False)

    try:
        documents = db.fetch_query("SELECT * FROM documents")
        print(documents)
    finally:
        db.close_connection()
