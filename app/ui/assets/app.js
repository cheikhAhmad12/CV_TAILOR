const tokenStatus = document.getElementById("token-status");
const profilesOutput = document.getElementById("profiles-output");
const jobsOutput = document.getElementById("jobs-output");
const tailorOutput = document.getElementById("tailor-output");
const docxLink = document.getElementById("docx-link");
const pdfLink = document.getElementById("pdf-link");

let token = localStorage.getItem("cv_tailor_token") || "";
renderToken();

function renderToken() {
  tokenStatus.textContent = token ? "connecté" : "non connecté";
}

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const text = await response.text();

  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!response.ok) {
    throw new Error(`${response.status}: ${pretty(data)}`);
  }

  return data;
}

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);
  const payload = {
    email: form.get("email"),
    full_name: form.get("full_name"),
    password: form.get("password"),
  };

  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    alert(`Compte créé: ${data.email}`);
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);
  const payload = {
    email: form.get("email"),
    password: form.get("password"),
  };

  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    token = data.access_token;
    localStorage.setItem("cv_tailor_token", token);
    renderToken();
    alert("Connecté.");
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);
  const payload = {
    title: form.get("title"),
    github_username: form.get("github_username"),
    master_cv_text: form.get("master_cv_text"),
  };

  try {
    const data = await api("/profiles/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    profilesOutput.textContent = pretty(data);
  } catch (err) {
    profilesOutput.textContent = err.message;
  }
});

document.getElementById("load-profiles").addEventListener("click", async () => {
  try {
    const data = await api("/profiles/");
    profilesOutput.textContent = pretty(data);
    if (Array.isArray(data) && data[0]) {
      document.querySelector("input[name='profile_id']").value = data[0].id;
    }
  } catch (err) {
    profilesOutput.textContent = err.message;
  }
});

document.getElementById("job-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);
  const payload = {
    title: form.get("title"),
    source_url: form.get("source_url"),
    raw_text: form.get("raw_text"),
  };

  try {
    const data = await api("/jobs/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    jobsOutput.textContent = pretty(data);
  } catch (err) {
    jobsOutput.textContent = err.message;
  }
});

document.getElementById("load-jobs").addEventListener("click", async () => {
  try {
    const data = await api("/jobs/");
    jobsOutput.textContent = pretty(data);
    if (Array.isArray(data) && data[0]) {
      document.querySelector("input[name='job_posting_id']").value = data[0].id;
    }
  } catch (err) {
    jobsOutput.textContent = err.message;
  }
});

document.getElementById("tailor-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);
  const payload = {
    profile_id: Number(form.get("profile_id")),
    job_posting_id: Number(form.get("job_posting_id")),
    github_projects: [],
    master_cv_latex: form.get("master_cv_latex") || "",
    use_llm: false,
  };

  try {
    const data = await api("/tailoring/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    tailorOutput.textContent = pretty(data);

    if (data.docx_path) {
      docxLink.href = `/exports/docx?path=${encodeURIComponent(data.docx_path)}`;
    }
    if (data.pdf_path) {
      pdfLink.href = `/exports/pdf?path=${encodeURIComponent(data.pdf_path)}`;
    }
  } catch (err) {
    tailorOutput.textContent = err.message;
  }
});
