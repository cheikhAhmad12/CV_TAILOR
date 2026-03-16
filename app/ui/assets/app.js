const authView = document.getElementById("auth-view");
const appView = document.getElementById("app-view");
const tokenStatus = document.getElementById("token-status");
const profilesOutput = document.getElementById("profiles-output");
const jobsOutput = document.getElementById("jobs-output");
const tailorOutput = document.getElementById("tailor-output");
const cvLink = document.getElementById("cv-link") || document.getElementById("pdf-link");
const letterLink = document.getElementById("letter-link") || document.getElementById("docx-link");
const compiledCvFrame = document.getElementById("compiled-cv-frame");

const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const logoutBtn = document.getElementById("logout-btn");
const refreshProfileBtn = document.getElementById("refresh-profile");
const registerProfileTextInput = document.getElementById("register-profile-text-input");
const registerProfileLatexInput = document.getElementById("register-profile-latex-input");
const registerProfilePdfInput = document.getElementById("register-profile-pdf-input");

let token = localStorage.getItem("cv_tailor_token") || "";
const latexByProfile = JSON.parse(localStorage.getItem("cv_tailor_latex_by_profile") || "{}");
let defaultProfileId = null;
let compiledCvObjectUrl = "";

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

function latexToPlainText(latex) {
  return String(latex || "")
    .replace(/%.*$/gm, "")
    .replace(/\\begin\{[^}]+\}/g, "")
    .replace(/\\end\{[^}]+\}/g, "")
    .replace(/\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{([^}]*)\})?/g, "$3")
    .replace(/&/g, " ")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function setDownloadLinks(pdfPath = "", letterPath = "") {
  if (!cvLink || !letterLink) {
    return;
  }

  if (pdfPath) {
    cvLink.href = `/exports/pdf?path=${encodeURIComponent(pdfPath)}`;
    cvLink.classList.remove("disabled");
  } else {
    cvLink.href = "#";
    cvLink.classList.add("disabled");
  }

  if (letterPath) {
    letterLink.href = `/exports/letter?path=${encodeURIComponent(letterPath)}`;
    letterLink.classList.remove("disabled");
  } else {
    letterLink.href = "#";
    letterLink.classList.add("disabled");
  }
}

function setRegisterProfileFormat(format) {
  const isText = format === "text";
  const isLatex = format === "latex";
  const isPdf = format === "pdf";

  registerProfileTextInput.classList.toggle("hidden", !isText);
  registerProfileLatexInput.classList.toggle("hidden", !isLatex);
  registerProfilePdfInput.classList.toggle("hidden", !isPdf);

  registerProfileTextInput.required = isText;
  registerProfileLatexInput.required = isLatex;
}

function switchAuthTab(tab) {
  const loginActive = tab === "login";

  tabLogin.classList.toggle("active", loginActive);
  tabRegister.classList.toggle("active", !loginActive);
  loginForm.classList.toggle("active", loginActive);
  registerForm.classList.toggle("active", !loginActive);
}

function setAuthState(isConnected) {
  if (!authView || !appView || !tokenStatus) {
    return;
  }

  authView.classList.toggle("active", !isConnected);
  appView.classList.toggle("active", isConnected);
  tokenStatus.textContent = isConnected ? "connecté" : "non connecté";
  if (!isConnected) {
    defaultProfileId = null;
    if (compiledCvObjectUrl) {
      URL.revokeObjectURL(compiledCvObjectUrl);
      compiledCvObjectUrl = "";
    }
    compiledCvFrame.src = "about:blank";
    compiledCvFrame.classList.add("hidden");
    profilesOutput.textContent = "";
  }
}

async function showCompiledPdf(pdfPath) {
  if (compiledCvObjectUrl) {
    URL.revokeObjectURL(compiledCvObjectUrl);
    compiledCvObjectUrl = "";
  }

  const response = await fetch(`/exports/pdf-inline?path=${encodeURIComponent(pdfPath || "")}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Preview failed (${response.status}): ${text || "unknown error"}`);
  }

  const blob = await response.blob();
  compiledCvObjectUrl = URL.createObjectURL(blob);
  compiledCvFrame.src = `${compiledCvObjectUrl}#toolbar=1&navpanes=0`;
  compiledCvFrame.classList.remove("hidden");
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
    if (response.status === 401) {
      token = "";
      localStorage.removeItem("cv_tailor_token");
      setAuthState(false);
    }
    throw new Error(`${response.status}: ${pretty(data)}`);
  }

  return data;
}

async function loginUser(email, password) {
  const data = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  token = data.access_token;
  localStorage.setItem("cv_tailor_token", token);
  setAuthState(true);
}

async function verifyGithubUsername(username) {
  const clean = String(username || "").trim();
  if (!clean) {
    return true;
  }
  const data = await api(`/github/validate?username=${encodeURIComponent(clean)}`);
  return Boolean(data.valid);
}

async function loadDefaultProfile() {
  const data = await api("/profiles/");
  if (!Array.isArray(data) || data.length === 0) {
    defaultProfileId = null;
    if (compiledCvObjectUrl) {
      URL.revokeObjectURL(compiledCvObjectUrl);
      compiledCvObjectUrl = "";
    }
    compiledCvFrame.src = "about:blank";
    compiledCvFrame.classList.add("hidden");
    profilesOutput.textContent = "Aucun profil trouvé. Réinscris-toi pour créer ton profil master.";
    return;
  }

  const profile = data[0];
  defaultProfileId = profile.id;

  if (profile.master_cv_latex) {
    latexByProfile[String(profile.id)] = String(profile.master_cv_latex);
    localStorage.setItem("cv_tailor_latex_by_profile", JSON.stringify(latexByProfile));
  }

  if (profile.master_cv_latex) {
    try {
      const compiled = await api(`/profiles/${profile.id}/compiled-pdf`);
      await showCompiledPdf(compiled.pdf_path || "");
      profilesOutput.textContent = pretty({
        id: profile.id,
        title: profile.title,
        github_username: profile.github_username,
        latex_present: true,
      });
      return;
    } catch (err) {
      if (compiledCvObjectUrl) {
        URL.revokeObjectURL(compiledCvObjectUrl);
        compiledCvObjectUrl = "";
      }
      compiledCvFrame.src = "about:blank";
      compiledCvFrame.classList.add("hidden");
      profilesOutput.textContent = `Compilation PDF impossible: ${err.message}`;
      return;
    }
  }

  if (compiledCvObjectUrl) {
    URL.revokeObjectURL(compiledCvObjectUrl);
    compiledCvObjectUrl = "";
  }
  compiledCvFrame.src = "about:blank";
  compiledCvFrame.classList.add("hidden");
  profilesOutput.textContent = pretty({
    id: profile.id,
    title: profile.title,
    github_username: profile.github_username,
    cv_preview: String(profile.master_cv_text || "").slice(0, 1200),
    latex_present: false,
  });
}

switchAuthTab("login");
setRegisterProfileFormat("text");
setDownloadLinks("", "");
setAuthState(Boolean(token));

if (token) {
  loadDefaultProfile().catch((err) => {
    profilesOutput.textContent = err.message;
  });
}

tabLogin.addEventListener("click", () => switchAuthTab("login"));
tabRegister.addEventListener("click", () => switchAuthTab("register"));

logoutBtn.addEventListener("click", () => {
  token = "";
  localStorage.removeItem("cv_tailor_token");
  setAuthState(false);
  setDownloadLinks("", "");
});

refreshProfileBtn.addEventListener("click", async () => {
  try {
    await loadDefaultProfile();
  } catch (err) {
    profilesOutput.textContent = err.message;
  }
});

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);

  try {
    await loginUser(form.get("email"), form.get("password"));
    await loadDefaultProfile();
    alert("Connecté.");
  } catch (err) {
    alert(err.message);
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.currentTarget);

  const registerPayload = {
    email: form.get("email"),
    full_name: form.get("full_name"),
    password: form.get("password"),
  };
  const githubUsername = String(form.get("github_username") || "").trim();

  const registerFormat = form.get("register_profile_format");
  if (registerFormat === "pdf") {
    alert("Import PDF pas encore disponible. Choisis Texte ou LaTeX.");
    return;
  }

  const latexSource = String(form.get("master_cv_latex") || "").trim();
  const textSource = String(form.get("master_cv_text") || "").trim();
  let masterCvText = "";

  if (registerFormat === "latex") {
    if (!latexSource) {
      alert("Le CV master (LaTeX) est requis.");
      return;
    }
    masterCvText = latexToPlainText(latexSource) || latexSource;
  } else {
    masterCvText = textSource;
    if (!masterCvText) {
      alert("Le CV master (texte) est requis.");
      return;
    }
  }

  try {
    if (githubUsername) {
      const isGithubValid = await verifyGithubUsername(githubUsername);
      if (!isGithubValid) {
        alert("Le username GitHub est invalide.");
        return;
      }
    }

    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify(registerPayload),
    });

    await loginUser(registerPayload.email, registerPayload.password);

    const profilePayload = {
      title: "Master CV",
      master_cv_text: masterCvText,
      master_cv_latex: registerFormat === "latex" ? latexSource : "",
      github_username: githubUsername,
    };

    const profile = await api("/profiles/", {
      method: "POST",
      body: JSON.stringify(profilePayload),
    });

    if (typeof profile.id !== "undefined") {
      latexByProfile[String(profile.id)] = profilePayload.master_cv_latex || "";
      localStorage.setItem("cv_tailor_latex_by_profile", JSON.stringify(latexByProfile));
      defaultProfileId = profile.id;
    }
    await loadDefaultProfile();

    alert("Compte créé, profil initial enregistré, et connexion réussie.");
  } catch (err) {
    alert(err.message);
  }
});

document.querySelectorAll("input[name='register_profile_format']").forEach((input) => {
  input.addEventListener("change", () => setRegisterProfileFormat(input.value));
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

  if (!defaultProfileId) {
    tailorOutput.textContent = "Aucun profil master trouvé pour ce compte.";
    return;
  }

  const payload = {
    profile_id: defaultProfileId,
    job_posting_id: Number(form.get("job_posting_id")),
    github_projects: [],
    master_cv_latex: latexByProfile[String(defaultProfileId)] || "",
    output_language: form.get("output_language") || "fr",
    use_llm: form.get("use_llm") === "on",
  };

  try {
    const data = await api("/tailoring/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    tailorOutput.textContent = pretty(data);
    setDownloadLinks(data.pdf_path || "", data.cover_letter_path || "");
  } catch (err) {
    tailorOutput.textContent = err.message;
    setDownloadLinks("", "");
  }
});
