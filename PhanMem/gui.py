"""Giao diện Tkinter: 5 thẻ. Chỉ gọi hàm của các module khác, không tự tính toán."""
import csv
import os
import queue
import statistics
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import benchmark
import database
import monitor
from file_reader import hash_file

STATUS_COLOR = {"OK": "#2e7d32", "MODIFIED": "#c62828", "MISSING": "#ef6c00", "ERROR": "#607d8b"}
STATUS_TEXT = {"OK": "Nguyên vẹn", "MODIFIED": "Đã bị thay đổi",
               "MISSING": "Không tìm thấy", "ERROR": "Lỗi đọc"}


def fmt_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % n
        n /= 1024


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Phần mềm kiểm tra tính toàn vẹn tập tin")
        self.geometry("980x600")
        self.minsize(820, 520)
        self.q = queue.Queue()
        self.last_status = {}           # file_id -> trạng thái lần quét gần nhất
        self.scan_new_hash = {}         # file_id -> hash mới của lần quét gần nhất
        self.algo = tk.StringVar(value="SHA-1")
        nb = self.nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_hash = ttk.Frame(nb)
        self.tab_list = ttk.Frame(nb)
        self.tab_check = ttk.Frame(nb)
        self.tab_hist = ttk.Frame(nb)
        self.tab_bench = ttk.Frame(nb)
        for f, name in ((self.tab_hash, "Tính hash"), (self.tab_list, "Danh sách giám sát"),
                        (self.tab_check, "Kiểm tra toàn vẹn"), (self.tab_hist, "Lịch sử"),
                        (self.tab_bench, "So sánh hiệu năng")):
            nb.add(f, text=name)
        self._build_hash()
        self._build_list()
        self._build_check()
        self._build_hist()
        self._build_bench()
        self.refresh_files()
        self.after(100, self._poll)

    # ---------- chạy nền: tránh đơ giao diện ----------
    def run_bg(self, work, done, progress=None):
        def target():
            try:
                res = work((lambda a, b: self.q.put(("p", progress, a, b))) if progress else None)
                self.q.put(("d", done, res, None))
            except Exception as e:  # noqa
                self.q.put(("e", None, e, None))
        threading.Thread(target=target, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, fn, a, b = self.q.get_nowait()
                if kind == "p" and fn:
                    fn(a, b)
                elif kind == "d":
                    fn(a)
                elif kind == "e":
                    messagebox.showerror("Lỗi", str(a))
        except queue.Empty:
            pass
        self.after(100, self._poll)

    # ---------- thẻ 1: Tính hash ----------
    def _build_hash(self):
        f = self.tab_hash
        f.columnconfigure(1, weight=1)
        self.path_var = tk.StringVar()
        ttk.Label(f, text="File:").grid(row=0, column=0, padx=12, pady=(24, 8), sticky="w")
        ttk.Entry(f, textvariable=self.path_var).grid(row=0, column=1, sticky="ew", pady=(24, 8))
        ttk.Button(f, text="Chọn file", command=self.pick_file).grid(row=0, column=2, padx=12, pady=(24, 8))
        ttk.Label(f, text="Thuật toán:").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        box = ttk.Frame(f)
        box.grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(box, text="SHA-1", variable=self.algo, value="SHA-1").pack(side="left", padx=(0, 20))
        ttk.Radiobutton(box, text="SHA-512", variable=self.algo, value="SHA-512").pack(side="left")
        btns = ttk.Frame(f)
        btns.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=12)
        ttk.Button(btns, text="Tính hash", command=lambda: self.compute(False)).pack(side="left", padx=(0, 10))
        ttk.Button(btns, text="Đăng ký giám sát", command=lambda: self.compute(True)).pack(side="left")
        ttk.Label(f, text="Kết quả:").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self.result_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.result_var, state="readonly",
                  font=("Courier", 10)).grid(row=3, column=1, sticky="ew")
        ttk.Button(f, text="Sao chép", command=self.copy_result).grid(row=3, column=2, padx=12)
        self.info_var = tk.StringVar()
        ttk.Label(f, textvariable=self.info_var).grid(row=4, column=0, columnspan=3, padx=12, pady=8, sticky="w")

    def pick_file(self):
        p = filedialog.askopenfilename()
        if p:
            self.path_var.set(p)

    def copy_result(self):
        self.clipboard_clear()
        self.clipboard_append(self.result_var.get())

    def compute(self, register):
        path, algo = self.path_var.get().strip(), self.algo.get()
        if not path:
            messagebox.showwarning("Thiếu thông tin", "Hãy chọn tập tin trước.")
            return
        self.info_var.set("Đang tính...")

        def work(_):
            t0 = time.perf_counter()
            h, err = hash_file(path, algo)
            return h, err, (time.perf_counter() - t0) * 1000

        def done(res):
            h, err, ms = res
            if err:
                self.result_var.set("")
                self.info_var.set("")
                messagebox.showerror("Lỗi", err)
                return
            size = os.path.getsize(path)
            self.result_var.set(h)
            self.info_var.set("Thời gian: %.1f ms    Kích thước: %s" % (ms, fmt_size(size)))
            if register:
                if database.add_file(os.path.abspath(path), algo, h, size):
                    messagebox.showinfo("Thành công", "Đã đăng ký giám sát tập tin.")
                    self.refresh_files()
                else:
                    messagebox.showinfo("Đã có", "Tập tin này đã đăng ký với thuật toán này.")
        self.run_bg(work, done)

    # ---------- thẻ 2: Danh sách giám sát ----------
    def _build_list(self):
        f = self.tab_list
        cols = ("path", "algo", "hash", "date", "status")
        self.tree_list = ttk.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c, t, w in zip(cols, ("Tập tin", "Thuật toán", "Hash đã lưu", "Ngày đăng ký", "Trạng thái gần nhất"),
                           (260, 80, 280, 130, 140)):
            self.tree_list.heading(c, text=t)
            self.tree_list.column(c, width=w)
        self.tree_list.pack(fill="both", expand=True, padx=8, pady=8)
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        for text, cmd in (("Thêm file", self.add_files), ("Thêm thư mục", self.add_folder),
                          ("Xóa khỏi danh sách", self.remove_selected), ("Cập nhật hash", self.update_selected)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=(0, 8))

    def _register_paths(self, paths):
        algo = self.algo.get()

        def work(prog):
            added = dup = bad = 0
            for i, p in enumerate(paths, 1):
                h, err = hash_file(p, algo)
                if err:
                    bad += 1
                elif database.add_file(os.path.abspath(p), algo, h, os.path.getsize(p)):
                    added += 1
                else:
                    dup += 1
                if prog:
                    prog(i, len(paths))
            return added, dup, bad

        def done(res):
            self.refresh_files()
            messagebox.showinfo("Kết quả", "Thêm mới: %d\nĐã có: %d\nLỗi đọc: %d  (thuật toán %s)" % (*res, algo))
        self.run_bg(work, done)

    def add_files(self):
        paths = filedialog.askopenfilenames()
        if paths:
            self._register_paths(paths)

    def add_folder(self):
        d = filedialog.askdirectory()
        if d:
            paths = [os.path.join(r, n) for r, _, fs in os.walk(d) for n in fs]
            self._register_paths(paths)

    def _selected_ids(self, tree):
        return [int(i) for i in tree.selection()]

    def remove_selected(self):
        ids = self._selected_ids(self.tree_list)
        if ids and messagebox.askyesno("Xác nhận", "Xóa %d mục khỏi danh sách giám sát?" % len(ids)):
            for i in ids:
                database.delete_file(i)
            self.refresh_files()

    def update_selected(self):
        ids = self._selected_ids(self.tree_list)
        if not ids:
            messagebox.showinfo("Chưa chọn", "Hãy chọn dòng cần cập nhật hash.")
            return
        if not messagebox.askyesno("Xác nhận", "Dùng hash hiện tại của tập tin làm giá trị chuẩn mới?"):
            return
        recs = {r[0]: r for r in database.get_all_files()}

        def work(_):
            ok = 0
            for i in ids:
                h, err = hash_file(recs[i][1], recs[i][2])
                if not err:
                    database.update_hash(i, h, os.path.getsize(recs[i][1]))
                    self.last_status[i] = "OK"
                    ok += 1
            return ok

        def done(ok):
            self.refresh_files()
            messagebox.showinfo("Kết quả", "Đã cập nhật %d/%d mục." % (ok, len(ids)))
        self.run_bg(work, done)

    def refresh_files(self):
        self.records = database.get_all_files()
        for t in (self.tree_list, self.tree_check):
            t.delete(*t.get_children())
        for r in self.records:
            st = self.last_status.get(r[0], "")
            self.tree_list.insert("", "end", iid=str(r[0]), values=(r[1], r[2], r[3], r[5], st))
            self.tree_check.insert("", "end", iid=str(r[0]), values=(r[1], r[2], st, ""),
                                   tags=(st,) if st else ())

    # ---------- thẻ 3: Kiểm tra toàn vẹn ----------
    def _build_check(self):
        f = self.tab_check
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Kiểm tra tất cả", command=lambda: self.check(False)).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Kiểm tra mục đã chọn", command=lambda: self.check(True)).pack(side="left")
        self.progress = ttk.Progressbar(bar, length=200)
        self.progress.pack(side="right")
        cols = ("path", "algo", "status", "msg")
        self.tree_check = ttk.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c, t, w in zip(cols, ("Tập tin", "Thuật toán", "Trạng thái", "Ghi chú"), (330, 90, 110, 300)):
            self.tree_check.heading(c, text=t)
            self.tree_check.column(c, width=w)
        for s, c in STATUS_COLOR.items():
            self.tree_check.tag_configure(s, foreground=c)
        self.tree_check.pack(fill="both", expand=True, padx=8)
        self.tree_check.bind("<<TreeviewSelect>>", self.show_detail)
        self.detail = tk.StringVar(value="Chọn một dòng để xem hash cũ và hash mới.")
        ttk.Label(f, textvariable=self.detail, font=("Courier", 9), justify="left").pack(
            anchor="w", padx=8, pady=8)

    def check(self, only_selected):
        ids = self._selected_ids(self.tree_check) if only_selected else None
        recs = [r for r in self.records if ids is None or r[0] in ids]
        if not recs:
            messagebox.showinfo("Trống", "Không có tập tin nào để kiểm tra.")
            return
        self.progress.configure(maximum=len(recs), value=0)

        def work(prog):
            return monitor.check_all(recs, prog)

        def prog(a, b):
            self.progress.configure(value=a)

        def done(results):
            for rec, status, new in results:
                self.last_status[rec[0]] = status
                self.scan_new_hash[rec[0]] = new
            self.refresh_files()
            for rec, status, _ in results:
                self.tree_check.item(str(rec[0]), values=(rec[1], rec[2], status, STATUS_TEXT[status]),
                                     tags=(status,))
            bad = sum(1 for _, s, _ in results if s != "OK")
            messagebox.showinfo("Hoàn tất", "Đã kiểm tra %d tập tin, %d bất thường." % (len(results), bad))
        self.run_bg(work, done, prog)

    def show_detail(self, _e):
        sel = self.tree_check.selection()
        if not sel:
            return
        i = int(sel[0])
        rec = next((r for r in self.records if r[0] == i), None)
        if rec:
            self.detail.set("Hash cũ : %s\nHash mới: %s" % (rec[3], self.scan_new_hash.get(i) or "(chưa kiểm tra)"))

    # ---------- thẻ 4: Lịch sử ----------
    def _build_hist(self):
        f = self.tab_hist
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Label(bar, text="Trạng thái:").pack(side="left")
        self.filter_var = tk.StringVar(value="Tất cả")
        cb = ttk.Combobox(bar, textvariable=self.filter_var, state="readonly", width=12,
                          values=("Tất cả", "OK", "MODIFIED", "MISSING", "ERROR"))
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda e: self.load_history())
        ttk.Button(bar, text="Làm mới", command=self.load_history).pack(side="left")
        ttk.Button(bar, text="Xuất ra CSV", command=self.export_csv).pack(side="right")
        cols = ("time", "path", "algo", "status", "hash")
        self.tree_hist = ttk.Treeview(f, columns=cols, show="headings")
        for c, t, w in zip(cols, ("Thời gian", "Tập tin", "Thuật toán", "Trạng thái", "Hash tính được"),
                           (140, 280, 80, 90, 300)):
            self.tree_hist.heading(c, text=t)
            self.tree_hist.column(c, width=w)
        self.tree_hist.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.nb.bind("<<NotebookTabChanged>>",
                     lambda e: self.load_history() if self.nb.index(self.nb.select()) == 3 else None)

    def load_history(self):
        self.tree_hist.delete(*self.tree_hist.get_children())
        self.hist_rows = database.get_history(self.filter_var.get())
        for r in self.hist_rows:
            self.tree_hist.insert("", "end", values=r)

    def export_csv(self):
        self.load_history()
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if p:
            with open(p, "w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh)
                w.writerow(["Thời gian", "Tập tin", "Thuật toán", "Trạng thái", "Hash"])
                w.writerows(self.hist_rows)
            messagebox.showinfo("Xong", "Đã xuất %d dòng." % len(self.hist_rows))

    # ---------- thẻ 5: So sánh hiệu năng ----------
    def _build_bench(self):
        f = self.tab_bench
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Chọn file test", command=self.pick_bench).pack(side="left")
        ttk.Label(bar, text="  Số lần chạy:").pack(side="left")
        self.runs_var = tk.IntVar(value=3)
        ttk.Spinbox(bar, from_=3, to=20, textvariable=self.runs_var, width=4).pack(side="left", padx=6)
        ttk.Button(bar, text="Chạy đo", command=self.run_bench).pack(side="left", padx=8)
        self.bench_files = []
        self.bench_label = tk.StringVar(value="Chưa chọn file test.")
        ttk.Label(f, textvariable=self.bench_label).pack(anchor="w", padx=8)
        cols = ("file", "algo", "runs", "avg", "std")
        self.tree_bench = ttk.Treeview(f, columns=cols, show="headings", height=6)
        for c, t, w in zip(cols, ("Tập tin", "Thuật toán", "Từng lần (ms)", "Trung bình (ms)", "Độ lệch (ms)"),
                           (200, 90, 330, 110, 100)):
            self.tree_bench.heading(c, text=t)
            self.tree_bench.column(c, width=w)
        self.tree_bench.pack(fill="x", padx=8, pady=8)
        self.canvas = tk.Canvas(f, height=200, bg="white", highlightthickness=1, highlightbackground="#999")
        self.canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def pick_bench(self):
        ps = filedialog.askopenfilenames()
        if ps:
            self.bench_files = list(ps)
            self.bench_label.set("Đã chọn %d file: %s" % (len(ps), ", ".join(os.path.basename(p) for p in ps)))

    def run_bench(self):
        if not self.bench_files:
            messagebox.showwarning("Thiếu file", "Hãy chọn file test trước.")
            return
        runs = max(3, int(self.runs_var.get()))
        files = list(self.bench_files)
        self.bench_label.set("Đang đo...")
        self.run_bg(lambda prog: benchmark.run_benchmark(files, runs),
                    self.show_bench)

    def show_bench(self, res):
        self.tree_bench.delete(*self.tree_bench.get_children())
        self.bench_label.set("Đã đo xong.")
        bars = []
        for (name, algo), ts in res.items():
            avg = statistics.mean(ts)
            sd = statistics.pstdev(ts)
            self.tree_bench.insert("", "end", values=(name, algo, "  ".join("%.1f" % t for t in ts),
                                                      "%.2f" % avg, "%.2f" % sd))
            bars.append(("%s\n%s" % (name, algo), avg, algo))
        c = self.canvas
        c.delete("all")
        c.update_idletasks()
        W, H = max(c.winfo_width(), 300), max(c.winfo_height(), 150)
        top = max(b[1] for b in bars) or 1
        bw = min(70, (W - 40) / (len(bars) * 1.5))
        for i, (label, avg, algo) in enumerate(bars):
            x0 = 30 + i * bw * 1.5
            h = (H - 60) * avg / top
            c.create_rectangle(x0, H - 35 - h, x0 + bw, H - 35,
                               fill="#1f4e79" if algo == "SHA-1" else "#7f7f7f", outline="")
            c.create_text(x0 + bw / 2, H - 35 - h - 8, text="%.1f" % avg, font=("TkDefaultFont", 8))
            c.create_text(x0 + bw / 2, H - 18, text=label, font=("TkDefaultFont", 8))
