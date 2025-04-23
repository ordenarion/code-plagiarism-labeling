import os
import zipfile
import csv
import streamlit as st
from streamlit_cookies_controller import CookieController
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session
from streamlit_js_eval import streamlit_js_eval
from pathlib import PurePath
import time

import pandas as pd
import io

from .config import config
from .models import SessionLocal, HW, Pair, User, default_user
from .utils import hash_password, verify_password, RoleEnum

session = scoped_session(SessionLocal)

controller = CookieController()


def check_admin(username, password):
    return username == config.ADMIN_LOGIN and password == config.ADMIN_PASSWORD


def login(username, password):
    if check_admin(username, password):
        save_user_to_cookies(default_user)
        st.experimental_set_query_params(page="Dashboard")
        st.success(f"Welcome!")

    user = session.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password):
        save_user_to_cookies(user)
        if user:
            st.experimental_set_query_params(page="Dashboard")
            st.success(f"Welcome {user.username} ({user.role})!")
        else:
            st.error("Invalid username or password.")


def get_logged_in_user():
    if controller.get('role'):
        st.session_state["role"] = controller.get('role')
    if controller.get('user_id'):
        st.session_state["user_id"] = controller.get("user_id")
    print(st.session_state)


def save_user_to_cookies(user: User | None):
    controller.set('role', user.role)
    controller.set('user_id', str(user.user_id))


def clear_user_cookies():
    controller.remove('role')
    controller.remove('user_id')


def admin_only(func):
    def wrapper(*args, **kwargs):
        if st.session_state.get("role") != "admin":
            st.error("Access denied. Admins only.")
            return
        return func(*args, **kwargs)

    return wrapper


def login_required(func):
    def wrapper(*args, **kwargs):
        if st.session_state.get("role") not in (RoleEnum.admin, RoleEnum.teacher):
            st.error("Access denied. Please log in.")
            return
        return func(*args, **kwargs)

    return wrapper

def export_hw_data(hw_entries):
    output = io.StringIO()  
    writer = csv.writer(output)
    writer.writerow(["HW_ID", "Text", "Cluster", "Name"])
    for hw in hw_entries:
        writer.writerow([hw.hw_id, hw.text, hw.cluster, hw.name])
    output.seek(0)
    return output.getvalue().encode("utf-8")  

def export_pair_data(pairs):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["HW_From_ID", "HW_To_ID", "User_ID", "Label", "Comment"])
    for pair in pairs:
        writer.writerow(
            [pair.hw_from_id, pair.hw_to_id, pair.user_id, pair.label, pair.comment]
        )
    output.seek(0)
    return output.getvalue().encode("utf-8")  # Преобразуем в байты



@admin_only
def user_management_page():
    st.title("User Management")

    users = session.query(User).all()
    st.subheader("Existing Users")
    for user in users:
        st.text(f"ID: {user.user_id}, Username: {user.username}, Role: {user.role}")

    st.subheader("Create New User")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    new_role = st.selectbox("Role", ["admin", "teacher"])
    if st.button("Create User"):
        new_user = User(
            username=new_username, password=hash_password(new_password), role=new_role
        )
        try:
            session.add(new_user)
            session.commit()
            st.success("User created successfully.")
        except IntegrityError:
            session.rollback()
            st.error("Username already exists.")

    st.subheader("Update User Role")
    user_id_to_update = st.number_input("User ID to update", min_value=1, step=1)
    new_role_for_update = st.selectbox("New Role", ["admin", "teacher"])
    if st.button("Update Role"):
        user_to_update = session.query(User).get(user_id_to_update)
        if user_to_update:
            user_to_update.role = new_role_for_update
            session.commit()
            st.success("Role updated successfully.")
        else:
            st.error("User not found.")

    st.subheader("Delete User")
    user_id_to_delete = st.number_input("User ID to delete", min_value=1, step=1)
    if st.button("Delete User"):
        user_to_delete = session.query(User).get(user_id_to_delete)
        if user_to_delete:
            session.delete(user_to_delete)
            session.commit()
            st.success("User deleted successfully.")
        else:
            st.error("User not found.")
@admin_only
def hw_list_page():
    st.title("Dashboard")
    st.write("Welcome to the Dashboard! You are logged in.")

    hw_entries = session.query(HW).all()
    st.subheader("HW Entries")

    selected_hw_ids = []

    def select_all():
        for hw in hw_entries:
            st.session_state[f"select_{hw.hw_id}"] = True

    if st.button("Select All HW"):
        select_all()

    for hw in hw_entries:
        col1, col2, col3 = st.columns([2, 6, 2])
        with col1:
            if f"select_{hw.hw_id}" not in st.session_state:
                st.session_state[f"select_{hw.hw_id}"] = False
            selected = st.checkbox("Select", key=f"select_{hw.hw_id}")
            if selected:
                selected_hw_ids.append(hw.hw_id)
        with col2:
            st.text(f"ID: {hw.hw_id}, Cluster: {hw.cluster}, Name: {hw.name}")
            st.text_area("Text", hw.text, height=100, disabled=True, key=str(hw.hw_id))
        with col3:
            if st.button(f"Delete HW {hw.hw_id}", key=f"delete_{hw.hw_id}"):
                hw_to_delete = session.query(HW).get(hw.hw_id)
                if hw_to_delete:
                    session.delete(hw_to_delete)
                    session.commit()
                    st.success(f"HW {hw.hw_id} deleted successfully.")
                else:
                    st.error(f"HW {hw.hw_id} not found.")

    if st.button("Delete Selected HW"):
        for hw_id in selected_hw_ids:
            hw_to_delete = session.query(HW).get(hw_id)
            if hw_to_delete:
                session.delete(hw_to_delete)
        session.commit()
        st.success("Selected HW entries deleted successfully.")


@admin_only
def hw_upload_page():
    st.title("HW Upload")

    uploaded_file = st.file_uploader("Upload a ZIP file", type="zip")
    if uploaded_file is not None:
        try:
            with zipfile.ZipFile(uploaded_file) as zf:
                all_files = [f for f in zf.namelist() if f.endswith(".txt")]
                for file_path in all_files:
                    path = PurePath(file_path)
                    if len(path.parts) < 3:
                        continue
                    cluster_name = path.parts[0]       
                    student_name = path.parts[1]       

                    with zf.open(file_path) as txt_file:
                        text_content = txt_file.read().decode("utf-8")
                        hw_entity = HW(
                            text=text_content,
                            cluster=cluster_name,
                            name=student_name,
                        )
                        session.add(hw_entity)

                session.commit()
                st.success("HW entities created successfully.")
        except Exception as e:
            session.rollback()
            st.error(f"An error occurred: {e}")


@login_required
def hw_labeling_page():
    st.title("HW Labeling")
    clusters = session.query(HW.cluster).distinct()
    cluster_selector = st.selectbox('Cluster select', options=clusters)

    hw_entries = session.query(HW).filter_by(cluster=cluster_selector).all()


    hw_ids = [hw.hw_id for hw in hw_entries]
    col1, col2 = st.columns(2)
    with col1:
        left_hw_id = st.selectbox(
            "Select HW for Left Side", options=hw_ids, key="left_selector"
        )
    with col2:
        right_hw_id = st.selectbox(
            "Select HW for Right Side",
            options=[hw_id for hw_id in hw_ids if hw_id > left_hw_id],
            key="right_selector",
        )

    left_hw = session.query(HW).get(left_hw_id)
    right_hw = session.query(HW).get(right_hw_id)

    st.subheader("Selected HW Texts")
    with col1:
        st.text_area(
            "Left HW Text", left_hw.text if left_hw else "", height=200, disabled=True
        )
    with col2:
        st.text_area(
            "Right HW Text",
            right_hw.text if right_hw else "",
            height=200,
            disabled=True,
        )
        pair = (
            session.query(Pair)
            .filter_by(
                user_id=st.session_state.get("user_id"),
                hw_from_id=left_hw.hw_id,
                hw_to_id=right_hw.hw_id,
            )
            .first()
        )
    comment_value = pair.comment if pair else ""
    plag_value = pair.label == 1 if pair else False
    st.subheader("Add Details for the Pair")
    comment = st.text_area("Comment", key="comment_field", value=comment_value)
    is_plagiarism = st.checkbox(
        "Is Plagiarism", key="plagiarism_checkbox", value=plag_value
    )

    if st.button("Save Pair"):
        if left_hw and right_hw:
            try:
                if pair:
                    pair.comment = comment
                    pair.label = 1 if is_plagiarism else 0
                    session.add(pair)
                else:
                    new_pair = Pair(
                        hw_from_id=left_hw.hw_id,
                        hw_to_id=right_hw.hw_id,
                        user_id=st.session_state.get(
                            "user_id"
                        ),  
                        label=1 if is_plagiarism else 0,
                        comment=comment,
                    )
                    session.add(new_pair)
                session.commit()
                st.success("Pair saved successfully.")
            except IntegrityError as e:
                print(e)
                session.rollback()
                st.error("Failed to save the pair. It might already exist.")
        else:
            st.error("Both HWs must be selected to save the pair.")


    st.subheader("Export Data")
    if st.button("Export HW"):
        hw_data = export_hw_data(hw_entries)
        st.download_button(
            label="Download HW CSV",
            data=hw_data,
            file_name="hw_data.csv",
            mime="text/csv",
        )

    if st.button("Export Pairs"):
        pairs = session.query(Pair).all()
        pair_data = export_pair_data(pairs)
        st.download_button(
            label="Download Pairs CSV",
            data=pair_data,
            file_name="pairs_data.csv",
            mime="text/csv",
        )

def main():
    get_logged_in_user()

    menu = ["Login", "HW List", "HW Labeling", "HW Upload", "User Management"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            login(username, password)

    elif choice == "HW List":
        hw_list_page()

    elif choice == "HW Labeling":
        hw_labeling_page()

    elif choice == "User Management":
        user_management_page()

    elif choice == "HW Upload":
        hw_upload_page()

    if st.sidebar.button("Logout"):
        st.session_state["role"] = None
        clear_user_cookies()
        streamlit_js_eval(js_expressions="parent.window.location.reload()")