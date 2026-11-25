const taskList = document.getElementById("taskList");
const emptyState = document.getElementById("emptyState");
const form = document.getElementById("taskForm");
const taskInput = document.getElementById("taskInput");
const priorityInput = document.getElementById("priorityInput");
const dateInput = document.getElementById("dateInput");
const searchInput = document.getElementById("searchInput");
const filters = [...document.querySelectorAll(".filter")];
let tasks = [];
let activeFilter = "all";
let toastTimer;

document.getElementById("todayLabel").textContent =
  new Intl.DateTimeFormat(undefined, { weekday:"short", month:"short", day:"numeric" }).format(new Date());

function notify(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2300);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

async function loadTasks() {
  try {
    tasks = await api("/api/tasks");
    render();
  } catch (error) {
    notify(error.message);
  }
}

function render() {
  const total = tasks.length;
  const done = tasks.filter(t => t.completed).length;
  const pending = total - done;
  const percent = total ? Math.round(done / total * 100) : 0;

  document.getElementById("totalCount").textContent = total;
  document.getElementById("doneCount").textContent = done;
  document.getElementById("pendingCount").textContent = pending;
  document.getElementById("allTabCount").textContent = total;
  document.getElementById("progressPercent").textContent = `${percent}%`;
  document.getElementById("progressFill").style.width = `${percent}%`;
  document.getElementById("progressTitle").textContent =
    total === 0 ? "Let's get started" : percent === 100 ? "Amazing work — all done!" : `${done} of ${total} tasks completed`;

  const query = searchInput.value.trim().toLowerCase();
  const visible = tasks.filter(task => {
    const matchesFilter = activeFilter === "all" ||
      (activeFilter === "pending" && !task.completed) ||
      (activeFilter === "completed" && task.completed);
    return matchesFilter && task.title.toLowerCase().includes(query);
  });

  taskList.innerHTML = "";
  visible.forEach(task => {
    const row = document.createElement("article");
    row.className = `task-row ${task.completed ? "is-done" : ""}`;

    const check = document.createElement("button");
    check.className = "check-btn";
    check.type = "button";
    check.textContent = task.completed ? "✓" : "";
    check.setAttribute("aria-label", task.completed ? "Mark as pending" : "Mark as completed");
    check.addEventListener("click", () => toggleTask(task));

    const content = document.createElement("div");
    const title = document.createElement("div");
    title.className = "task-title";
    title.textContent = task.title;
    const meta = document.createElement("div");
    meta.className = "task-meta";
    meta.textContent = task.due_date ? `Due ${formatDate(task.due_date)}` : "No due date";
    content.append(title, meta);

    const priority = document.createElement("span");
    priority.className = `priority ${task.priority}`;
    priority.textContent = task.priority;

    const del = document.createElement("button");
    del.className = "delete-btn";
    del.type = "button";
    del.textContent = "×";
    del.setAttribute("aria-label", "Delete task");
    del.addEventListener("click", () => deleteTask(task));

    row.append(check, content, priority, del);
    taskList.appendChild(row);
  });

  const showEmpty = visible.length === 0;
  emptyState.style.display = showEmpty ? "block" : "none";
  if (showEmpty) {
    emptyState.querySelector("h4").textContent = query ? "No matching tasks" :
      (activeFilter === "completed" ? "No completed tasks yet" : activeFilter === "pending" ? "No pending tasks" : "Nothing on your list yet");
  }
}

function formatDate(value) {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat(undefined, { month:"short", day:"numeric", year:"numeric" }).format(date);
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const title = taskInput.value.trim();
  if (!title) return;
  try {
    await api("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title, priority: priorityInput.value, due_date: dateInput.value })
    });
    taskInput.value = "";
    dateInput.value = "";
    priorityInput.value = "Medium";
    await loadTasks();
    notify("Task added successfully ✨");
    taskInput.focus();
  } catch (error) {
    notify(error.message);
  }
});

async function toggleTask(task) {
  try {
    await api(`/api/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: !task.completed })
    });
    await loadTasks();
    notify(task.completed ? "Moved back to pending" : "Great job — task completed!");
  } catch (error) { notify(error.message); }
}

async function deleteTask(task) {
  if (!confirm(`Delete "${task.title}"?`)) return;
  try {
    await api(`/api/tasks/${task.id}`, { method: "DELETE" });
    await loadTasks();
    notify("Task deleted");
  } catch (error) { notify(error.message); }
}

document.getElementById("clearCompleted").addEventListener("click", async () => {
  if (!tasks.some(t => t.completed)) return notify("There are no completed tasks.");
  if (!confirm("Delete all completed tasks?")) return;
  try {
    await api("/api/tasks", { method: "DELETE" });
    await loadTasks();
    notify("Completed tasks cleared");
  } catch (error) { notify(error.message); }
});

filters.forEach(button => button.addEventListener("click", () => {
  activeFilter = button.dataset.filter;
  filters.forEach(item => item.classList.toggle("active", item === button));
  render();
}));
searchInput.addEventListener("input", render);

loadTasks();
