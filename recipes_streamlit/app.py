from __future__ import annotations

import pandas as pd
import streamlit as st
from bson import ObjectId

from mongo import get_db, ensure_indexes
import services


st.set_page_config(page_title="Recepti", layout="wide")


@st.cache_resource
def init_db():
    db = get_db()
    ensure_indexes(db)
    return db


db = init_db()

def ensure_state():
    if "saved_ids" not in st.session_state:
        st.session_state["saved_ids"] = set()
    if "results_all" not in st.session_state:
        st.session_state["results_all"] = None
    if "results_search" not in st.session_state:
        st.session_state["results_search"] = None
    if "results_pantry" not in st.session_state:
        st.session_state["results_pantry"] = None

ensure_state()


def require_login() -> bool:
    return st.session_state.get("user") is not None


def logout():
    st.session_state["user"] = None
    st.session_state["login_tries"] = {}
    st.rerun()


def show_auth():
    st.title("login / registracija")

    if "login_tries" not in st.session_state:
        st.session_state["login_tries"] = {}  

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Korisničko ime", key="login_username")
            password = st.text_input("Lozinka", type="password", key="login_password")
            submitted = st.form_submit_button("Ulogiraj se")

        if submitted:
            u = (username or "").strip()
            if not u or not password:
                st.error("Unesi korisničko ime i lozinku.")
                return

            tries = st.session_state["login_tries"].get(u, 0)
            if tries >= 3:
                st.error("Previše pogrešnih pokušaja za ovog korisnika.")
                return

            user, err = services.login(db, u, password)
            if err:
                st.session_state["login_tries"][u] = tries + 1
                st.error(f"{err} (pokušaj {tries+1}/3)")
            else:
                st.session_state["user"] = user
                st.success(f"Ulogiran korisnik: {user.get('username')}")
                st.rerun()
                st.session_state["user"] = user
                refresh_saved_ids(user)


    with tab2:
        st.subheader("Register")
        with st.form("register_form", clear_on_submit=False):
            username = st.text_input("Korisničko ime", key="reg_username")
            display_name = st.text_input("Display name (opcionalno)", key="reg_display")
            pw1 = st.text_input("Lozinka", type="password", key="reg_pw1")
            pw2 = st.text_input("Ponovi lozinku", type="password", key="reg_pw2")
            submitted = st.form_submit_button("Registriraj se")

        if submitted:
            u = (username or "").strip()
            if not u:
                st.error("Username ne smije biti prazan.")
                return
            if pw1 != pw2:
                st.error("Lozinke se ne poklapaju.")
                return
            if len(pw1) < 3:
                st.error("Prekratka lozinka (demo).")
                return

            user, err = services.register(db, u, pw1, display_name.strip() or u)
            if err:
                st.error(err)
            else:
                st.session_state["user"] = user
                st.success("Korisnik kreiran i ulogiran.")
                st.rerun()


def dataframe_from_recipes(recipes):

    rows = []
    for r in recipes:
        rr = services.serialize_doc(r)
        rr["_id"] = str(r.get("_id")) if r.get("_id") else rr.get("_id")
        rows.append(rr)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def render_recipe_cards(recipes, user, saved_ids: set[ObjectId] | None = None, show_match=False):
    if not recipes:
        st.info("Nema rezultata.")
        return

    if saved_ids is None:
        saved_ids = set()

    for r in recipes:
        rid_raw = r.get("_id")

        try:
            rid = services.to_objectid(rid_raw)
        except Exception:
            rid = None

        rid_str = str(rid) if rid else "(no id)"
        title = r.get("title", "(no title)")
        author = r.get("author_username") or "unknown"
        created = r.get("created_at")

        header = f"{title}  —  autor: {author}  |  id: {rid_str}"
        with st.expander(header, expanded=False):
            cols = st.columns([1, 1, 1])

            with cols[0]:
                st.write("**Allergens:**", r.get("allergens", []))
                st.write("**Ingredient keys:**", r.get("ingredient_keys", []))

            with cols[1]:
                st.write("**Saves:**", int(r.get("save_count", 0)))
                st.write("**Comments:**", int(r.get("comment_count", 0)))
                st.write("**Created:**", created)

            with cols[2]:
                if rid is None:
                    st.warning("Nije moguće spremiti ovaj recept (neispravan _id).")
                else:
                    is_saved = rid in saved_ids
                    if not is_saved:
                        if st.button("Spremi", key=f"save_{rid_str}"):
                            ok, msg = services.save_recipe(db, user["_id"], rid)
                            if ok:
                                refresh_saved_ids(user)
                                st.success(msg)
                            else:
                                st.warning(msg)
                            st.rerun()
                    else:
                        if st.button("Ukloni iz spremljenih", key=f"unsave_{rid_str}"):
                            ok, msg = services.unsave_recipe(db, user["_id"], rid)
                            if ok:
                                refresh_saved_ids(user)
                                st.success(msg)
                            else:
                                st.warning(msg)
                            st.rerun()

            if show_match:
                st.write("**Match count:**", r.get("match_count", 0))
                st.write("**Match keys:**", r.get("match_keys", []))

            if rid is not None:
                st.markdown("---")
                st.write("### Komentari")

                if st.button("Učitaj komentare", key=f"load_comments_{rid_str}"):
                    st.session_state[f"comments_loaded_{rid_str}"] = True

                if st.session_state.get(f"comments_loaded_{rid_str}", False):
                    recipe_title, comments, err = services.list_comments_for_recipe(db, rid)
                    if err:
                        st.error(err)
                    else:
                        if not comments:
                            st.info("Nema komentara.")
                        else:
                            for c in comments:
                                au = c.get("author_username") or "unknown"
                                st.write(f"- **[{au}]** {c.get('text')} ({c.get('created_at')})")

                new_comment = st.text_input("Dodaj komentar", key=f"comment_text_{rid_str}")
                if st.button("Spremi komentar", key=f"add_comment_{rid_str}"):
                    ok, msg = services.add_comment(db, user["_id"], rid, new_comment)
                    st.success(msg) if ok else st.error(msg)
                    st.session_state[f"comments_loaded_{rid_str}"] = True
                    st.rerun()


def page_add_recipe(user):
    st.header("Dodaj recept")

    with st.form("add_recipe_form", clear_on_submit=True):
        title = st.text_input("Naslov")
        description = st.text_area("Opis (opcionalno)")

        st.subheader("Sastojci")

        df = pd.DataFrame([{"name": "", "qty": None, "unit": ""}])
        ingredients_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key="ingredients_editor"
        )

        st.subheader("Koraci")
        steps_text = st.text_area("Jedan korak po retku", height=150, placeholder="Korak 1...\nKorak 2...\n...")

        submitted = st.form_submit_button("Spremi recept")

    if submitted:
        if not title.strip():
            st.error("Naslov ne smije biti prazan.")
            return

        ingredients_input = []
        for _, row in ingredients_df.iterrows():
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            qty = row.get("qty", None)
            unit = str(row.get("unit") or "").strip()
            ingredients_input.append({"name": name, "qty": qty, "unit": unit})

        steps = [s.strip() for s in (steps_text or "").splitlines() if s.strip()]

        try:
            rid, keys, allergens = services.create_recipe(
                db=db,
                user_id=user["_id"],
                title=title,
                description=description,
                ingredients_input=ingredients_input,
                steps=steps,
            )
            st.success("✅ Recept spremljen!")
            st.write("**id:**", str(rid))
            st.write("**ingredient_keys:**", keys)
            st.write("**allergens:**", allergens)
        except Exception as e:
            st.error(f"Greška: {e}")


def page_my_recipes(user):
    st.header("Moji recepti")
    recipes = services.list_my_recipes(db, user["_id"], limit=50)
    if not recipes:
        st.info("Nema recepata.")
        return


    for r in recipes:
        st.write(f"- **{r.get('title')}** | id={r.get('_id')} | keys={r.get('ingredient_keys', [])} | allergens={r.get('allergens', [])}")


def page_all_recipes(user):
    st.header("Svi recepti (s saves/comments count)")

    with st.form("form_all_recipes"):
        col1, col2 = st.columns([2, 1])
        with col1:
            username = st.text_input("Filtriraj po username (prazno = svi)", key="all_username")
        with col2:
            limit = st.number_input("Limit", min_value=1, max_value=500, value=50, step=10, key="all_limit")

        submitted = st.form_submit_button("Prikaži")

    if submitted:
        st.session_state["results_all"] = services.list_all_recipes_enriched(
            db, username=username, limit=int(limit)
        )

    if st.session_state["results_all"] is not None:

        st.session_state["saved_ids"] = services.get_saved_recipe_ids(db, user["_id"])
        render_recipe_cards(
            st.session_state["results_all"],
            user,
            saved_ids=st.session_state["saved_ids"],
            show_match=False,
        )


def page_search(user):
    st.header("Pretraga po sastojcima (AND/OR/NOT + alergeni)")

    with st.form("form_search"):
        col1, col2 = st.columns(2)
        with col1:
            inc = st.text_input("Include (AND), npr: piletina,riza", key="s_inc")
            any_of = st.text_input("Any-of (OR), npr: banana,orah", key="s_any")
        with col2:
            exc = st.text_input("Exclude (NOT), npr: cesnjak", key="s_exc")
            exa = st.text_input("Exclude allergens, npr: mlijeko,gluten", key="s_exa")

        limit = st.number_input("Limit", min_value=1, max_value=500, value=50, step=10, key="s_limit")
        submitted = st.form_submit_button("Traži")

    if submitted:
        st.session_state["results_search"] = services.search_by_ingredients_enriched(
            db, inc_csv=inc, any_csv=any_of, exc_csv=exc, exa_csv=exa, limit=int(limit)
        )

    if st.session_state["results_search"] is not None:
        st.session_state["saved_ids"] = services.get_saved_recipe_ids(db, user["_id"])
        render_recipe_cards(
            st.session_state["results_search"],
            user,
            saved_ids=st.session_state["saved_ids"],
            show_match=False,
        )

def page_pantry(user):
    st.header("'Imam doma'")

    with st.form("form_pantry"):
        pantry = st.text_input("Sastojci koje imaš (zarez), npr: piletina, luk, riza", key="p_pantry")
        min_match = st.number_input("Minimalno poklapanja", min_value=1, max_value=50, value=1, step=1, key="p_min")
        exa = st.text_input("Exclude allergens (opcionalno), npr: mlijeko,gluten", key="p_exa")
        limit = st.number_input("Limit", min_value=1, max_value=500, value=50, step=10, key="p_limit")
        submitted = st.form_submit_button("Rangiraj")

    if submitted:
        if not pantry.strip():
            st.error("Unesi barem jedan sastojak.")
        else:
            st.session_state["results_pantry"] = services.pantry_ranked_search_enriched(
                db, pantry_csv=pantry, min_match=int(min_match), exa_csv=exa, limit=int(limit)
            )

    if st.session_state["results_pantry"] is not None:
        st.session_state["saved_ids"] = services.get_saved_recipe_ids(db, user["_id"])
        render_recipe_cards(
            st.session_state["results_pantry"],
            user,
            saved_ids=st.session_state["saved_ids"],
            show_match=True,
        )


def page_saved(user):
    st.header("Moji spremljeni recepti")
    results = services.list_saved_recipes(db, user["_id"], limit=50)
    if not results:
        st.info("Nema spremljenih recepata.")
        return

    for r in results:
        st.write(f"- **{r['title']}** | autor={r.get('author_username')} | id={r['recipe_id']} | saved_at={r['saved_at']}")


def page_save_count(user):
    st.header("Broj spremanja recepta")
    rid_raw = st.text_input("Unesi recipe id (ObjectId string)")
    if st.button("Provjeri"):
        try:
            title, n, err = services.save_count(db, rid_raw)
            if err:
                st.error(err)
            else:
                st.success(f"'{title}' je spremljen {n} puta.")
        except Exception as e:
            st.error(f"Greška: {e}")

def refresh_saved_ids(user):
    st.session_state["saved_ids"] = services.get_saved_recipe_ids(db, user["_id"])

def ensure_state():
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "saved_ids" not in st.session_state:
        st.session_state["saved_ids"] = set()
    if "results_all" not in st.session_state:
        st.session_state["results_all"] = None
    if "results_search" not in st.session_state:
        st.session_state["results_search"] = None
    if "results_pantry" not in st.session_state:
        st.session_state["results_pantry"] = None

def main():
    # top bar
    ensure_state()
    user = st.session_state.get("user")
    if not user:
        show_auth()
        return

    st.sidebar.title("Navigacija")
    st.sidebar.write(f"Ulogiran: **{user.get('username')}**")
    if st.sidebar.button("Logout"):
        logout()

    page = st.sidebar.selectbox(
        "Odaberi",
        [
            "Dodaj recept",
            "Moji recepti",
            "Svi recepti",
            "Pretraga",
            "Imam doma (rangirano)",
            "Spremljeni",
        ],
    )

    if page == "Dodaj recept":
        page_add_recipe(user)
    elif page == "Moji recepti":
        page_my_recipes(user)
    elif page == "Svi recepti":
        page_all_recipes(user)
    elif page == "Pretraga":
        page_search(user)
    elif page == "Imam doma (rangirano)":
        page_pantry(user)
    elif page == "Spremljeni":
        page_saved(user)



if __name__ == "__main__":

    if "user" not in st.session_state:
        st.session_state["user"] = None
    main()
