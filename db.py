import sqlite3


class Database:
    def __init__(self):
        if __name__ == "__main__":
            self.connection = sqlite3.connect("./bills.db")
        else:
            self.connection = sqlite3.connect("./bills.db", check_same_thread=False)

        self.cursor = self.connection.cursor()
        self.execute = self.cursor.execute

    def insertOne(self, bill_id: int, name: str, price: float, control_number: str):
        queryData = [bill_id, name, price, control_number]
        self.execute(
            "INSERT INTO bills(bill_id, name, price, control_number) VALUES(?, ?, ?, ?)",
            queryData,
        )
        self.connection.commit()

    def getData(self):
        self.execute("SELECT * FROM bills")
        return self.cursor.fetchall()

    def updateData(self, id: int, data: list):
        self.execute(
            f"UPDATE bills SET bill_id={data[0]} name='{data[1]}', price={data[2]}, control_number='{data[3]}' WHERE id={id}"
        )
        self.connection.commit()

    def deleteOFromDb(self, id: int):
        self.execute(f"DELETE FROM bills WHERE id = {id}")
        self.connection.commit()

    def deleteAll(self):
        self.execute("DELETE FROM bills")
        self.connection.commit()


if __name__ == "__main__":
    Database()


"""self.cursor.execute("CREATE TABLE IF NOT EXISTS bills(id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER(8) NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, control_number TEXT)")"""
