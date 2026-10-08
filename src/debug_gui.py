"""
Debug GUI: enter a card number, fetch the matching member via
members_db.get_member() (which applies normalize_card() internally),
and show exactly what was returned.

Run with: python debug_lookup_gui.py
Requires members_db.py in the same directory.
"""
import sqlite3
import tkinter as tk
from tkinter import ttk

import db


class DebugLookupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Member Lookup (debug)")
        self.geometry("480x320")
        self.resizable(False, False)

        db.init_db()
        self._build_widgets()

    def _build_widgets(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Card number:").pack(side="left")
        self.input_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.input_var)
        entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        entry.bind("<Return>", lambda _e: self.on_fetch())
        entry.focus_set()

        ttk.Button(top, text="Fetch", command=self.on_fetch).pack(side="left")

        self.status_var = tk.StringVar(value="Enter a card number and press Fetch.")
        ttk.Label(self, textvariable=self.status_var, foreground="#555").pack(
            anchor="w", padx=10
        )

        # Raw query info: what was typed vs what it normalized to.
        info = ttk.LabelFrame(self, text="Query")
        info.pack(fill="x", padx=10, pady=(5, 10))
        self.raw_var = tk.StringVar(value="raw input: —")
        self.normalized_var = tk.StringVar(value="normalized to: —")
        ttk.Label(info, textvariable=self.raw_var).pack(anchor="w", padx=8, pady=(4, 0))
        ttk.Label(info, textvariable=self.normalized_var).pack(anchor="w", padx=8, pady=(0, 4))

        # Result display
        result = ttk.LabelFrame(self, text="Result")
        result.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.fields = {}
        for row_idx, label in enumerate(["id", "card_number", "name", "boardmember", "comment"]):
            ttk.Label(result, text=f"{label}:").grid(row=row_idx, column=0, sticky="ne", padx=8, pady=4)
            var = tk.StringVar(value="—")
            ttk.Label(result, textvariable=var, wraplength=320, justify="left").grid(
                row=row_idx, column=1, sticky="nw", padx=8, pady=4
            )
            self.fields[label] = var

    def on_fetch(self):
        raw = self.input_var.get().strip()
        self.raw_var.set(f"raw input: {raw!r}")

        if not raw:
            self.status_var.set("Enter a card number first.")
            self._clear_fields()
            self.normalized_var.set("normalized to: —")
            return

        try:
            normalized = db.normalize_card(raw)
        except Exception as exc:  # noqa: BLE001 - debug tool, show whatever happens
            self.status_var.set(f"normalize_card() raised: {exc}")
            self.normalized_var.set("normalized to: —")
            self._clear_fields()
            return
        self.normalized_var.set(f"normalized to: {normalized!r}")

        try:
            row = db.get_member(raw)
        except sqlite3.Error as exc:
            self.status_var.set(f"Database error: {exc}")
            self._clear_fields()
            return

        if row is None:
            self.status_var.set("No member found for that card number.")
            self._clear_fields()
            return

        member_id, name, card_number, boardmember, comment = row
        self.fields["id"].set(member_id)
        self.fields["card_number"].set(card_number)
        self.fields["name"].set(name)
        self.fields["boardmember"].set("Yes" if boardmember else "No")
        self.fields["comment"].set(comment if comment is not None else "(none)")
        self.status_var.set("Match found.")

    def _clear_fields(self):
        for var in self.fields.values():
            var.set("—")


if __name__ == "__main__":
    app = DebugLookupApp()
    app.mainloop()