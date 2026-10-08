"""
Tkinter GUI for the members database: view, add, update, and remove rows.

Run with: python members_gui.py
Requires members_db.py in the same directory.
"""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

import db


class MemberApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Members")
        self.geometry("720x480")
        self.minsize(640, 420)

        self._selected_card_number = None  # original card_number of selected row, or None = add mode
        self._original = {}  # snapshot of selected row's values, for diffing on update

        self._build_widgets()
        db.init_db()
        self.refresh_tree()

    # ------------------------------------------------------------------ UI

    def _build_widgets(self):
        # --- Search ---
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_tree())
        ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side="left")
        ttk.Label(search_frame, text="(matches card number, name, or comment)", foreground="#777").pack(
            side="left", padx=(8, 0)
        )

        # --- Table ---
        columns = ("id", "card_number", "name", "boardmember", "comment")
        headings = {
            "id": "ID",
            "card_number": "Card Number",
            "name": "Name",
            "boardmember": "Board Member",
            "comment": "Comment",
        }
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=headings[col])
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("card_number", width=130)
        self.tree.column("name", width=180)
        self.tree.column("boardmember", width=100, anchor="center")
        self.tree.column("comment", width=180)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)

        # --- Form ---
        form = ttk.LabelFrame(self, text="Member details")
        form.pack(fill="x", padx=10, pady=5)
        for i in range(4):
            form.columnconfigure(i, weight=1)

        ttk.Label(form, text="Card number:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.card_number_var = tk.StringVar()
        self.card_number_entry = ttk.Entry(form, textvariable=self.card_number_var)
        self.card_number_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=4)

        ttk.Label(form, text="New card number\n(update only, optional):").grid(
            row=0, column=2, sticky="e", padx=5, pady=4
        )
        self.new_card_number_var = tk.StringVar()
        self.new_card_number_entry = ttk.Entry(form, textvariable=self.new_card_number_var)
        self.new_card_number_entry.grid(row=0, column=3, sticky="ew", padx=5, pady=4)

        ttk.Label(form, text="Name:").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var).grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        self.boardmember_var = tk.BooleanVar()
        ttk.Checkbutton(form, text="Board member", variable=self.boardmember_var).grid(
            row=1, column=2, sticky="w", padx=5, pady=4
        )

        ttk.Label(form, text="Comment:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        self.comment_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.comment_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=4
        )

        # --- Buttons ---
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btns, text="Add new", command=self.on_add).pack(side="left", padx=4)
        ttk.Button(btns, text="Update selected", command=self.on_update).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove selected", command=self.on_remove).pack(side="left", padx=4)
        ttk.Button(btns, text="Clear / new member", command=self.clear_form).pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    # -------------------------------------------------------------- helpers

    def set_status(self, text):
        self.status_var.set(text)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        query = self.search_var.get().strip().lower()
        for row in db.list_members():
            member_id, card_number, name, boardmember, comment = row
            if query and not self._row_matches(query, card_number, name, comment):
                continue
            self.tree.insert(
                "", "end",
                values=(member_id, card_number, name, "Yes" if boardmember else "No", comment or ""),
            )

    @staticmethod
    def _row_matches(query, card_number, name, comment):
        haystacks = (card_number or "", name or "", comment or "")
        return any(query in field.lower() for field in haystacks)

    def _clear_search(self):
        self.search_var.set("")
        self.refresh_tree()

    def clear_form(self):
        self.tree.selection_remove(self.tree.selection())
        self._selected_card_number = None
        self._original = {}
        self.card_number_entry.configure(state="normal")
        self.card_number_var.set("")
        self.new_card_number_var.set("")
        self.name_var.set("")
        self.boardmember_var.set(False)
        self.comment_var.set("")
        self.set_status("Ready to add a new member.")

    def on_select_row(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        _id, card_number, name, boardmember_display, comment = values

        self._selected_card_number = card_number
        self._original = {
            "name": name,
            "boardmember": 1 if boardmember_display == "Yes" else 0,
            "comment": comment or "",
        }

        self.card_number_var.set(card_number)
        self.card_number_entry.configure(state="readonly")
        self.new_card_number_var.set("")
        self.name_var.set(name)
        self.boardmember_var.set(boardmember_display == "Yes")
        self.comment_var.set(comment or "")
        self.set_status(f"Editing member with card number {card_number}.")

    # --------------------------------------------------------- validation

    def _validate_common(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Name is required.")
            return None
        return name

    # -------------------------------------------------------------- actions

    def on_add(self):
        card_number = self.card_number_var.get().strip()
        if not card_number:
            messagebox.showerror("Missing card number", "Card number is required.")
            return
        name = self._validate_common()
        if name is None:
            return
        boardmember = 1 if self.boardmember_var.get() else 0
        comment = self.comment_var.get().strip() or None

        try:
            db.add_member(card_number, name, boardmember=boardmember, comment=comment)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Duplicate card number",
                f"A member with card number '{card_number}' already exists.",
            )
            return
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc))
            return

        self.refresh_tree()
        self.clear_form()
        self.set_status(f"Added member '{name}'.")

    def on_update(self):
        if self._selected_card_number is None:
            messagebox.showerror("No selection", "Select a member in the table first.")
            return
        name = self._validate_common()
        if name is None:
            return
        boardmember = 1 if self.boardmember_var.get() else 0
        comment = self.comment_var.get().strip()
        new_card_number = self.new_card_number_var.get().strip()

        changes = {}
        if name != self._original["name"]:
            changes["name"] = name
        if boardmember != self._original["boardmember"]:
            changes["boardmember"] = boardmember
        if comment != self._original["comment"]:
            changes["comment"] = comment or None
        if new_card_number and new_card_number != self._selected_card_number:
            changes["new_card_number"] = new_card_number

        if not changes:
            self.set_status("No changes to save.")
            return

        try:
            updated = db.update_member(self._selected_card_number, **changes)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Update failed",
                "That card number is already assigned to another member.",
            )
            return
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc))
            return

        if not updated:
            messagebox.showerror("Not found", "That member no longer exists.")
            self.refresh_tree()
            self.clear_form()
            return

        self.refresh_tree()
        self.clear_form()
        self.set_status(f"Updated member '{name}'.")

    def on_remove(self):
        if self._selected_card_number is None:
            messagebox.showerror("No selection", "Select a member in the table first.")
            return
        name = self._original.get("name", "")
        if not messagebox.askyesno(
            "Confirm removal",
            f"Remove member '{name}' (card number {self._selected_card_number})?",
        ):
            return
        db.remove_member(self._selected_card_number)
        self.refresh_tree()
        self.clear_form()
        self.set_status("Member removed.")


if __name__ == "__main__":
    app = MemberApp()
    app.mainloop()
