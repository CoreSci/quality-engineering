// Reading list: a small static page used as the system under test.
// Plain JavaScript, no external assets. The list is kept in this browser's
// localStorage, so it survives a reload.
"use strict";

const STORAGE_KEY = "reading-list.v1";
const TITLE_MAX = 100;
const PAGES_MIN = 1;
const PAGES_MAX = 5000;
const STATUS_LABELS = { "to-read": "To read", "reading": "Reading", "done": "Done" };

const form = document.getElementById("add-form");
const titleInput = document.getElementById("title");
const pagesInput = document.getElementById("pages");
const statusSelect = document.getElementById("status");
const titleError = document.getElementById("title-error");
const pagesError = document.getElementById("pages-error");
const filterSelect = document.getElementById("filter");
const summary = document.getElementById("summary");
const list = document.getElementById("books");

let books = load();
let nextId = books.reduce((max, b) => Math.max(max, b.id), 0) + 1;

function load() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(data) ? data : [];
  } catch (e) {
    return [];
  }
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(books));
}

function setError(input, element, message) {
  element.textContent = message;
  if (message) {
    input.setAttribute("aria-invalid", "true");
  } else {
    input.removeAttribute("aria-invalid");
  }
}

// Returns {title, pages} or null; shows one message per invalid field.
function checkInput() {
  const title = titleInput.value.trim();
  const pagesText = pagesInput.value.trim();
  let titleMessage = "";
  let pagesMessage = "";

  if (!title) {
    titleMessage = "Enter a title.";
  } else if (title.length > TITLE_MAX) {
    titleMessage = `Use at most ${TITLE_MAX} characters.`;
  } else if (books.some((b) => b.title.toLowerCase() === title.toLowerCase())) {
    titleMessage = "This book is already on the list.";
  }

  if (!/^\d+$/.test(pagesText)) {
    pagesMessage = "Enter the number of pages as a whole number.";
  } else {
    const n = Number(pagesText);
    if (n < PAGES_MIN || n > PAGES_MAX) {
      pagesMessage = `Enter a number from ${PAGES_MIN} to ${PAGES_MAX}.`;
    }
  }

  setError(titleInput, titleError, titleMessage);
  setError(pagesInput, pagesError, pagesMessage);
  if (titleMessage) { titleInput.focus(); return null; }
  if (pagesMessage) { pagesInput.focus(); return null; }
  return { title, pages: Number(pagesText) };
}

function render() {
  const shown = filterSelect.value === "all" ? books : books.filter((b) => b.status === filterSelect.value);
  list.replaceChildren();
  for (const book of shown) {
    const item = document.createElement("li");
    const title = document.createElement("span");
    title.className = "book-title";
    title.textContent = book.title;                  // text, never HTML
    item.append(title, ` (${book.pages} pages, ${STATUS_LABELS[book.status]})`);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${book.title}`);
    remove.addEventListener("click", () => {
      books = books.filter((b) => b.id !== book.id);
      save();
      render();
    });
    item.append(remove);
    list.append(item);
  }
  const pages = shown.reduce((sum, b) => sum + b.pages, 0);
  summary.textContent = `${shown.length} of ${books.length} books shown, ${pages} pages`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const input = checkInput();
  if (!input) return;
  books.push({ id: nextId++, title: input.title, pages: input.pages, status: statusSelect.value });
  save();
  form.reset();
  titleInput.focus();
  render();
});

filterSelect.addEventListener("change", render);
render();
