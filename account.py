import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, Label, Entry, Button, filedialog
import configparser
import json
import pymysql
import pyperclip  # type: ignore

class EmailCodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("邮箱和代码提交")
        self.root.geometry("800x500")
        self.root.resizable(True, True)

        self.load_config()
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Helvetica', 10), padding=5)
        self.style.configure('TLabel', font=('Helvetica', 12))
        self.style.configure('TEntry', font=('Helvetica', 10), padding=5)

        self.create_widgets()
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")


    def load_config(self):
        self.config = configparser.ConfigParser()
        try:
            self.config.read('config.ini')
            self.db_host = self.config.get('database', 'host')
            self.db_user = self.config.get('database', 'user')
            self.db_password = self.config.get('database', 'password')
            self.db_name = self.config.get('database', 'name')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            messagebox.showerror("配置错误", f"配置文件中缺少部分: {e}")
            self.create_default_config()

    def create_default_config(self):
        self.config['database'] = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'name': 'test_db'
        }
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        messagebox.showinfo("配置文件生成", "已生成默认配置文件 config.ini")

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        self.rows = []
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.create_headers()
        self.add_row()

        self.add_row_button = ttk.Button(self.root, text="添加新行", command=self.add_row)
        self.add_row_button.pack(pady=10)

        self.add_db_button = ttk.Button(self.root, text="添加数据库", command=self.show_add_database_window)
        self.add_db_button.pack(pady=10)

        self.submit_button = ttk.Button(self.root, text="提交", command=self.confirm_submit)
        self.submit_button.pack(pady=10)

        self.import_button = ttk.Button(self.root, text="导入 account.json", command=self.import_data)
        self.import_button.pack(pady=10)

        self.load_data()

    def create_headers(self):
        ttk.Label(self.frame, text="邮箱").grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(self.frame, text="密码").grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(self.frame, text="已售出").grid(row=0, column=2, padx=5, pady=2)

    def add_row(self, email='', code='', sold=False):
        row = {}

        email_entry = ttk.Entry(self.frame, width=30)
        email_entry.grid(row=len(self.rows) + 1, column=0, padx=5, pady=2)
        email_entry.insert(0, email)
        row['email'] = email_entry

        code_entry = ttk.Entry(self.frame, width=30)
        code_entry.grid(row=len(self.rows) + 1, column=1, padx=5, pady=2)
        code_entry.insert(0, code)
        row['code'] = code_entry

        sold_var = tk.BooleanVar(value=sold)
        sold_check = ttk.Checkbutton(self.frame, variable=sold_var, text="已售出")
        sold_check.grid(row=len(self.rows) + 1, column=2, padx=5, pady=2)
        row['sold'] = sold_var

        copy_button = ttk.Button(self.frame, text="复制", command=lambda: self.copy_to_clipboard(email_entry.get(), code_entry.get()))
        copy_button.grid(row=len(self.rows) + 1, column=3, padx=5, pady=2)

        self.rows.append(row)

    def copy_to_clipboard(self, email, code):
        copy_text = f"账号: {email} ；密码: {code}"
        pyperclip.copy(copy_text)
        messagebox.showinfo("复制成功", "账号和密码已复制到粘贴板")

    def confirm_submit(self):
        result = messagebox.askyesno("提交", "是否同步到数据库？")
        self.submit_data(sync_to_db=result)

    def submit_data(self, sync_to_db):
        data = [{'email': row['email'].get(), 'code': row['code'].get(), 'sold': row['sold'].get()} for row in self.rows]
        
        with open('account.json', 'w') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        if sync_to_db:
            try:
                self.submit_to_database(data)
                messagebox.showinfo("提交", "数据已提交并同步到数据库")
            except Exception as e:
                messagebox.showerror("数据库错误", f"同步到数据库时出错: {e}")

    def submit_to_database(self, data):
        try:
            connection = pymysql.connect(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name)
            cursor = connection.cursor()
            for entry in data:
                cursor.execute(
                    "INSERT INTO email_codes (email, code, sold) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE code=%s, sold=%s",
                    (entry['email'], entry['code'], entry['sold'], entry['code'], entry['sold'])
                )
            connection.commit()
            cursor.close()
            connection.close()
        except pymysql.MySQLError as e:
            messagebox.showerror("数据库错误", f"数据库连接或查询时出错: {e}")

    def import_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r') as json_file:
                    data = json.load(json_file)
                    for entry in data:
                        self.add_row(entry['email'], entry['code'], entry['sold'])
            except FileNotFoundError:
                messagebox.showerror("文件错误", "文件未找到")
            except json.JSONDecodeError:
                messagebox.showerror("文件错误", "文件格式错误")

    def show_add_database_window(self):
        db_window = Toplevel(self.root)
        db_window.title("添加数据库")
        db_window.geometry("300x200")

        Label(db_window, text="数据库主机").pack(pady=5)
        db_host_entry = Entry(db_window)
        db_host_entry.pack(pady=5)

        Label(db_window, text="数据库用户").pack(pady=5)
        db_user_entry = Entry(db_window)
        db_user_entry.pack(pady=5)

        Label(db_window, text="数据库密码").pack(pady=5)
        db_password_entry = Entry(db_window, show="*")
        db_password_entry.pack(pady=5)

        Label(db_window, text="数据库名称").pack(pady=5)
        db_name_entry = Entry(db_window)
        db_name_entry.pack(pady=5)

        def save_db_config():
            self.db_host = db_host_entry.get()
            self.db_user = db_user_entry.get()
            self.db_password = db_password_entry.get()
            self.db_name = db_name_entry.get()
            db_window.destroy()

        Button(db_window, text="保存", command=save_db_config).pack(pady=10)

    def load_data(self):
        try:
            with open('account.json', 'r') as json_file:
                data = json.load(json_file)
                for entry in data:
                    self.add_row(entry['email'], entry['code'], entry['sold'])
        except FileNotFoundError:
            self.create_default_account_json()
        except json.JSONDecodeError:
            messagebox.showerror("文件错误", "account.json 文件格式错误")

    def create_default_account_json(self):
        default_data = []
        with open('account.json', 'w') as json_file:
            json.dump(default_data, json_file, ensure_ascii=False, indent=4)
        messagebox.showinfo("文件生成", "已生成默认 account.json 文件")

if __name__ == "__main__":
    root = tk.Tk()
    app = EmailCodeApp(root)
    root.mainloop()
