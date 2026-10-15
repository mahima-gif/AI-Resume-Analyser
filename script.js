// ================================
// CONFIG & AUTHENTICATION CHECK
// ================================
const API_BASE_URL = "http://127.0.0.1:8000";

let currentUser = {
    email: localStorage.getItem("userEmail") || "admin@gmail.com",
    name: localStorage.getItem("userName") || "Admin",
    title: localStorage.getItem("userTitle") || "Resume Analyst"
};

const isLoggedIn = localStorage.getItem("isLoggedIn");
if (isLoggedIn !== "true") {
    window.location.href = "login.html";
}

// Global state for interactive agents
let currentMockQuestions = [];
let currentMockIndex = 0;
let aptitudeQuestionsData = [];
let userAptitudeAnswers = {};
let latestAnalysisData = null;
let latestRebuiltResume = null;

// ================================
// DOM ELEMENTS & INITIALIZATION
// ================================
document.addEventListener("DOMContentLoaded", () => {
    initUserHeader();
    setupNavigation();
    setupFileUpload();
    setupAnalysis();
    setupRebuilderAndAutoApply();
    setupJobRecommendations();
    setupRoadmap();
    setupMockInterview();
    setupAptitudeTest();
    setupResumeTips();
    setupHistory();
    setupProfile();
    setupLogout();
    fetchDashboardStats();
});


function initUserHeader() {
    const welcomeUserHeading = document.getElementById("welcomeUserHeading");
    const topUserName = document.getElementById("topUserName");
    const topUserTitle = document.getElementById("topUserTitle");
    const topAvatar = document.getElementById("topAvatar");

    if (welcomeUserHeading) welcomeUserHeading.textContent = `Welcome back, ${currentUser.name} 👋`;
    if (topUserName) topUserName.textContent = currentUser.name;
    if (topUserTitle) topUserTitle.textContent = currentUser.title;
    if (topAvatar) topAvatar.textContent = currentUser.name.charAt(0).toUpperCase();
}

// ================================
// NAVIGATION (SPA VIEWS)
// ================================
function setupNavigation() {
    const navDashboard = document.getElementById("navDashboard");
    const navJobs = document.getElementById("navJobs");
    const navRoadmap = document.getElementById("navRoadmap");
    const navMock = document.getElementById("navMock");
    const navAptitude = document.getElementById("navAptitude");
    const navTips = document.getElementById("navTips");
    const navEtiquette = document.getElementById("navEtiquette");
    const navHistory = document.getElementById("navHistory");
    const navProfile = document.getElementById("navProfile");
    const topbarProfile = document.getElementById("topbarProfile");

    const views = {
        analyzer: document.getElementById("analyzerView"),
        jobs: document.getElementById("jobsView"),
        roadmap: document.getElementById("roadmapView"),
        mock: document.getElementById("mockView"),
        aptitude: document.getElementById("aptitudeView"),
        tips: document.getElementById("tipsView"),
        etiquette: document.getElementById("etiquetteView"),
        history: document.getElementById("historyView"),
        profile: document.getElementById("profileView")
    };

    const navItems = [navDashboard, navJobs, navRoadmap, navMock, navAptitude, navTips, navEtiquette, navHistory, navProfile];

    function switchView(viewKey) {
        Object.keys(views).forEach(k => {
            if (views[k]) views[k].style.display = (k === viewKey) ? "block" : "none";
        });

        navItems.forEach(el => el?.classList.remove("active"));

        if (viewKey === "analyzer") navDashboard?.classList.add("active");
        else if (viewKey === "jobs") { navJobs?.classList.add("active"); loadJobs(); }
        else if (viewKey === "roadmap") { navRoadmap?.classList.add("active"); loadRoadmap(); }
        else if (viewKey === "mock") { navMock?.classList.add("active"); loadMockQuestions(); }
        else if (viewKey === "aptitude") { navAptitude?.classList.add("active"); loadAptitudeTest(); }
        else if (viewKey === "tips") { navTips?.classList.add("active"); loadResumeTips(); }
        else if (viewKey === "etiquette") { navEtiquette?.classList.add("active"); }
        else if (viewKey === "history") { navHistory?.classList.add("active"); loadHistoryTable(); }
        else if (viewKey === "profile") { navProfile?.classList.add("active"); loadProfileView(); }
    }

    navDashboard?.addEventListener("click", (e) => { e.preventDefault(); switchView("analyzer"); });
    navJobs?.addEventListener("click", (e) => { e.preventDefault(); switchView("jobs"); });
    navRoadmap?.addEventListener("click", (e) => { e.preventDefault(); switchView("roadmap"); });
    navMock?.addEventListener("click", (e) => { e.preventDefault(); switchView("mock"); });
    navAptitude?.addEventListener("click", (e) => { e.preventDefault(); switchView("aptitude"); });
    navTips?.addEventListener("click", (e) => { e.preventDefault(); switchView("tips"); });
    navEtiquette?.addEventListener("click", (e) => { e.preventDefault(); switchView("etiquette"); });
    navHistory?.addEventListener("click", (e) => { e.preventDefault(); switchView("history"); });
    navProfile?.addEventListener("click", (e) => { e.preventDefault(); switchView("profile"); });
    topbarProfile?.addEventListener("click", () => { switchView("profile"); });
}

// ================================
// FILE UPLOAD HANDLING
// ================================
function setupFileUpload() {
    const resumeFile = document.getElementById("resumeFile");
    const chooseFileButton = document.getElementById("chooseFileButton");
    const selectedFile = document.getElementById("selectedFile");
    const uploadMessage = document.getElementById("uploadMessage");

    chooseFileButton?.addEventListener("click", () => resumeFile.click());

    resumeFile?.addEventListener("change", () => {
        if (resumeFile.files.length > 0) {
            const file = resumeFile.files[0];
            selectedFile.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            selectedFile.style.color = "#a7f3d0";
            if (uploadMessage) uploadMessage.textContent = "";
        } else {
            selectedFile.textContent = "No file selected";
            selectedFile.style.color = "var(--text-subtle)";
        }
    });
}

// ================================
// RESUME ANALYSIS EXECUTION
// ================================
function setupAnalysis() {
    const analyzeButton = document.getElementById("analyzeButton");
    const resumeFile = document.getElementById("resumeFile");
    const targetRoleSelect = document.getElementById("targetRoleSelect");
    const uploadMessage = document.getElementById("uploadMessage");

    analyzeButton?.addEventListener("click", async () => {
        if (!resumeFile.files || resumeFile.files.length === 0) {
            if (uploadMessage) {
                uploadMessage.textContent = "⚠️ Please choose a resume file (.pdf or .docx) first.";
                uploadMessage.style.color = "#fca5a5";
            }
            return;
        }

        const file = resumeFile.files[0];
        const targetRole = targetRoleSelect?.value || "general";

        const formData = new FormData();
        formData.append("file", file);
        formData.append("user_email", currentUser.email);
        formData.append("target_role", targetRole);

        analyzeButton.innerHTML = "<span>Parsing & Benchmarking...</span> <span>⏳</span>";
        analyzeButton.disabled = true;
        if (uploadMessage) {
            uploadMessage.textContent = "Running multi-factor parsing and ATS scoring engine...";
            uploadMessage.style.color = "#93c5fd";
        }

        try {
            const response = await fetch(`${API_BASE_URL}/analyze`, {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.status === "success") {
                if (uploadMessage) {
                    uploadMessage.textContent = "✅ Analysis complete & saved to history!";
                    uploadMessage.style.color = "#86efac";
                }

                latestAnalysisData = data;
                renderAnalysisResults(data);
                fetchDashboardStats();
            } else {
                const err = data.detail || "Analysis failed. Please check file format.";
                if (uploadMessage) {
                    uploadMessage.textContent = "❌ " + err;
                    uploadMessage.style.color = "#fca5a5";
                }
            }
        } catch (error) {
            console.error("Analysis Network Error:", error);
            if (uploadMessage) {
                uploadMessage.textContent = "❌ Could not connect to backend server. Make sure it is running.";
                uploadMessage.style.color = "#fca5a5";
            }
        } finally {
            analyzeButton.innerHTML = "<span>Execute ATS Analysis</span> <span>⚡</span>";
            analyzeButton.disabled = false;
        }
    });
}

function renderAnalysisResults(data) {
    latestAnalysisData = data;
    const resultsSection = document.getElementById("resultsSection");
    if (resultsSection) resultsSection.style.display = "block";

    // Reset Rebuild Banner
    const banner = document.getElementById("rebuildSuccessBanner");
    if (banner) banner.style.display = "none";
    const cardTitle = document.getElementById("extractedCardTitle");
    if (cardTitle) cardTitle.textContent = "Normalized Parsed Text (ATS Ingestion Stream)";

    const atsScore = document.getElementById("atsScore");
    const scoreMessage = document.getElementById("scoreMessage");
    const atsStat = document.getElementById("atsStat");

    if (atsScore) {
        atsScore.textContent = data.ats_score;
        if (data.ats_score >= 80) {
            atsScore.style.color = "#34d399";
            if (scoreMessage) scoreMessage.textContent = "🌟 Outstanding readiness! High probability of passing recruiter filters.";
        } else if (data.ats_score >= 60) {
            atsScore.style.color = "#fbbf24";
            if (scoreMessage) scoreMessage.textContent = "👍 Solid baseline. Applying key recommendations will elevate your ranking.";
        } else {
            atsScore.style.color = "#f87171";
            if (scoreMessage) scoreMessage.textContent = "⚠️ Action required: Click 'Rebuild to 100% ATS Ready' above to automatically upgrade your resume!";
        }
    }
    if (atsStat) atsStat.textContent = `${data.ats_score}/100`;

    // Badges
    const badgeEmail = document.getElementById("badgeEmail");
    const badgePhone = document.getElementById("badgePhone");
    const badgeLinks = document.getElementById("badgeLinks");

    if (badgeEmail) {
        badgeEmail.textContent = data.contact_info?.email ? "📧 Email: Present" : "📧 Email: Missing";
        badgeEmail.style.color = data.contact_info?.email ? "#86efac" : "#fca5a5";
    }
    if (badgePhone) {
        badgePhone.textContent = data.contact_info?.phone ? "📱 Phone: Present" : "📱 Phone: Missing";
        badgePhone.style.color = data.contact_info?.phone ? "#86efac" : "#fca5a5";
    }
    if (badgeLinks) {
        badgeLinks.textContent = data.contact_info?.links ? "🔗 Links: Present" : "🔗 Links: Missing";
        badgeLinks.style.color = data.contact_info?.links ? "#86efac" : "#fca5a5";
    }

    // Detected Skills
    const skillsList = document.getElementById("skillsList");
    const skillsStat = document.getElementById("skillsStat");
    if (skillsList) {
        skillsList.innerHTML = "";
        if (data.skills && data.skills.length > 0) {
            data.skills.forEach(skill => {
                const tag = document.createElement("span");
                tag.className = "skill-tag";
                tag.textContent = skill;
                skillsList.appendChild(tag);
            });
        } else {
            skillsList.innerHTML = '<span class="empty-result">No recognized technical skills found.</span>';
        }
    }
    if (skillsStat) skillsStat.textContent = data.skills ? data.skills.length : 0;

    // Missing Skills
    const missingSkillsList = document.getElementById("missingSkillsList");
    if (missingSkillsList) {
        missingSkillsList.innerHTML = "";
        if (data.missing_skills && data.missing_skills.length > 0) {
            data.missing_skills.forEach(skill => {
                const tag = document.createElement("span");
                tag.className = "skill-tag";
                tag.textContent = `+ ${skill}`;
                missingSkillsList.appendChild(tag);
            });
        } else {
            missingSkillsList.innerHTML = '<span class="empty-result" style="color:#86efac;">All recommended profile skills present!</span>';
        }
    }

    // Suggestions
    const suggestionsList = document.getElementById("suggestionsList");
    if (suggestionsList) {
        suggestionsList.innerHTML = "";
        if (data.suggestions && data.suggestions.length > 0) {
            data.suggestions.forEach(item => {
                const li = document.createElement("li");
                li.textContent = item;
                suggestionsList.appendChild(li);
            });
        }
    }

    // Extracted Text
    const extractedText = document.getElementById("extractedText");
    if (extractedText) {
        extractedText.textContent = data.extracted_text || "No text extracted.";
    }

    resultsSection?.scrollIntoView({ behavior: "smooth" });
}

// ================================
// RESUME REBUILDER & AUTO-APPLY AGENT
// ================================
function setupRebuilderAndAutoApply() {
    const rebuildBtn = document.getElementById("rebuild100Btn");
    const scoreCardRebuildBtn = document.getElementById("scoreCardRebuildBtn");
    const banner = document.getElementById("rebuildSuccessBanner");
    const autoApplyBtn = document.getElementById("autoApplyAllBtn");
    const startPrepBtn = document.getElementById("startInterviewPrepBtn");
    const copyBtn = document.getElementById("copyResumeTextBtn");
    const downloadPdfBtn = document.getElementById("downloadPdfBtn");
    const downloadDocxBtn = document.getElementById("downloadDocxBtn");
    const quickPdfBtn = document.getElementById("quickDownloadPdfBtn");
    const quickDocxBtn = document.getElementById("quickDownloadDocxBtn");

    // Download Function for PDF & DOCX
    async function triggerResumeDownload(format = "pdf", btnElement = null) {
        const targetRole = latestAnalysisData?.target_role || document.getElementById("targetRoleSelect")?.value || "software_engineer";
        const userName = currentUser.name || "Candidate";
        const userEmail = currentUser.email || "candidate@gmail.com";
        const endpoint = format === "pdf" ? "/career/download-pdf" : "/career/download-docx";

        let originalBtnHtml = "";
        if (btnElement) {
            originalBtnHtml = btnElement.innerHTML;
            btnElement.disabled = true;
            btnElement.innerHTML = `<span>Generating ${format.toUpperCase()}...</span> <span>⏳</span>`;
        }

        try {
            const res = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    extracted_text: latestRebuiltResume?.rebuilt_text || latestAnalysisData?.extracted_text || "Full Stack & Cloud Software Engineering Experience",
                    target_role: targetRole,
                    user_name: userName,
                    user_email: userEmail,
                    user_phone: "+1 (555) 019-2834"
                })
            });

            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = url;
            a.download = `${userName.replace(/\s+/g, '_')}_100_ATS_Resume.${format === "pdf" ? "pdf" : "docx"}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (err) {
            console.error(err);
            alert(`Failed to generate 100% ATS ${format.toUpperCase()} file. Please ensure the backend is running.`);
        } finally {
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.innerHTML = originalBtnHtml;
            }
        }
    }

    downloadPdfBtn?.addEventListener("click", () => triggerResumeDownload("pdf", downloadPdfBtn));
    downloadDocxBtn?.addEventListener("click", () => triggerResumeDownload("docx", downloadDocxBtn));
    quickPdfBtn?.addEventListener("click", () => triggerResumeDownload("pdf", quickPdfBtn));
    quickDocxBtn?.addEventListener("click", () => triggerResumeDownload("docx", quickDocxBtn));

    async function executeRebuildAction(triggerBtn) {
        const targetRole = latestAnalysisData?.target_role || document.getElementById("targetRoleSelect")?.value || "software_engineer";
        const textContent = latestAnalysisData?.extracted_text || "Software Development and Engineering Profile";

        const originalBtnText = triggerBtn ? triggerBtn.innerHTML : "";
        if (triggerBtn) {
            triggerBtn.disabled = true;
            triggerBtn.innerHTML = "<span>Generating 100% ATS Resume...</span> <span>⏳</span>";
        }

        try {
            const res = await fetch(`${API_BASE_URL}/career/rebuild-100`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    extracted_text: textContent,
                    target_role: targetRole,
                    user_name: currentUser.name || "Candidate",
                    user_email: currentUser.email || "candidate@gmail.com",
                    user_phone: "+1 (555) 019-2834"
                })
            });

            const data = await res.json();
            if (res.ok && data.status === "success") {
                latestRebuiltResume = data;

                // Make sure results section is visible
                const resultsSection = document.getElementById("resultsSection");
                if (resultsSection) resultsSection.style.display = "block";

                // 1. Upgrade Score Display to 100
                const atsScore = document.getElementById("atsScore");
                const atsStat = document.getElementById("atsStat");
                const scoreMessage = document.getElementById("scoreMessage");
                if (atsScore) {
                    atsScore.textContent = "100";
                    atsScore.style.color = "#34d399";
                }
                if (atsStat) atsStat.textContent = "100/100";
                if (scoreMessage) scoreMessage.textContent = "🎯 100% Perfect ATS Match! Candidate profile is completely optimized and ready for tier-1 interviews.";

                // 2. Show 100% Success Transformation Banner
                if (banner) banner.style.display = "block";

                // 3. Update Extracted Text View with Rebuilt High-Performance Resume
                const extractedText = document.getElementById("extractedText");
                const cardTitle = document.getElementById("extractedCardTitle");
                if (extractedText) extractedText.textContent = data.rebuilt_text;
                if (cardTitle) cardTitle.textContent = "✨ 100% ATS Optimized Resume (Ready for Direct Submission)";

                // 4. Update Skills with all target competencies
                const skillsList = document.getElementById("skillsList");
                const skillsStat = document.getElementById("skillsStat");
                if (skillsList && data.skills) {
                    skillsList.innerHTML = "";
                    data.skills.forEach(skill => {
                        const tag = document.createElement("span");
                        tag.className = "skill-tag";
                        tag.style.background = "rgba(16, 185, 129, 0.2)";
                        tag.style.borderColor = "rgba(16, 185, 129, 0.5)";
                        tag.style.color = "#a7f3d0";
                        tag.textContent = `✓ ${skill}`;
                        skillsList.appendChild(tag);
                    });
                }
                if (skillsStat && data.skills) skillsStat.textContent = data.skills.length;

                // 5. Clear missing skills
                const missingSkillsList = document.getElementById("missingSkillsList");
                if (missingSkillsList) {
                    missingSkillsList.innerHTML = '<span class="empty-result" style="color:#86efac; font-weight:700;">✓ 100% Competency Coverage Achieved! Zero Skill Gaps.</span>';
                }

                // 6. Update Suggestions to reflect 100% compliance
                const suggestionsList = document.getElementById("suggestionsList");
                if (suggestionsList) {
                    suggestionsList.innerHTML = `
                        <li style="color: #a7f3d0;">✓ <strong>100% Keyword Density:</strong> All critical frameworks and domain libraries for ${data.role_title} have been injected.</li>
                        <li style="color: #a7f3d0;">✓ <strong>XYZ Formula Metrics:</strong> Every professional experience bullet utilizes measurable business and engineering outcomes.</li>
                        <li style="color: #a7f3d0;">✓ <strong>ATS Parser Standard:</strong> Section headers, contact metadata, and bullet styles are 100% compatible with Workday, Taleo, and Greenhouse.</li>
                        <li style="color: #a7f3d0;">✓ <strong>Ready for Export:</strong> Click 'Download 100% ATS PDF' or 'Download Word (.docx)' above to save your document.</li>
                    `;
                }

                // 7. Update contact badges if not present
                const badgeEmail = document.getElementById("badgeEmail");
                const badgePhone = document.getElementById("badgePhone");
                const badgeLinks = document.getElementById("badgeLinks");
                if (badgeEmail) { badgeEmail.textContent = "📧 Email: Present (100%)"; badgeEmail.style.color = "#86efac"; }
                if (badgePhone) { badgePhone.textContent = "📱 Phone: Present (100%)"; badgePhone.style.color = "#86efac"; }
                if (badgeLinks) { badgeLinks.textContent = "🔗 Portfolio: Present (100%)"; badgeLinks.style.color = "#86efac"; }

                banner?.scrollIntoView({ behavior: "smooth" });
            }
        } catch (e) {
            console.error(e);
            alert("Failed to rebuild resume. Please verify backend server is running.");
        } finally {
            if (triggerBtn) {
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = originalBtnText;
            }
        }
    }

    rebuildBtn?.addEventListener("click", () => executeRebuildAction(rebuildBtn));
    scoreCardRebuildBtn?.addEventListener("click", () => executeRebuildAction(scoreCardRebuildBtn));

    // Copy Rebuilt Resume
    copyBtn?.addEventListener("click", () => {
        const text = document.getElementById("extractedText")?.textContent || "";
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = "✓ Copied to Clipboard!";
            setTimeout(() => { copyBtn.textContent = "📋 Copy Text"; }, 2000);
        });
    });

    // 1-Click Auto Apply All
    autoApplyBtn?.addEventListener("click", async () => {
        const targetRole = latestAnalysisData?.target_role || "software_engineer";
        autoApplyBtn.disabled = true;
        autoApplyBtn.innerHTML = "<span>Dispatching Applications...</span> <span>⏳</span>";

        try {
            const jobsRes = await fetch(`${API_BASE_URL}/career/jobs?role=${encodeURIComponent(targetRole)}`);
            const jobsData = await jobsRes.json();
            const jobs = jobsData.jobs || [];

            let successCount = 0;
            for (const job of jobs) {
                await fetch(`${API_BASE_URL}/career/auto-apply`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        job_title: job.title,
                        company: job.company,
                        portal: job.portal,
                        candidate_name: currentUser.name || "Candidate",
                        candidate_email: currentUser.email || "candidate@gmail.com",
                        ats_score: 100,
                        target_role: targetRole
                    })
                });
                successCount++;
            }

            alert(`🎉 Success! Automatically submitted 100% ATS Resume to all ${successCount} verified job openings on LinkedIn, Indeed, Naukri, and Wellfound!\n\nCandidate status is updated to: 'Interview Screening Ready'.`);
            
            // Switch to Jobs tab to see results
            document.getElementById("navJobs")?.click();

        } catch (e) {
            alert("Auto-application dispatcher encountered an issue.");
        } finally {
            autoApplyBtn.disabled = false;
            autoApplyBtn.innerHTML = "<span>🚀 1-Click Auto-Apply</span>";
        }
    });

    // Practice Mock Interview Quick Action
    startPrepBtn?.addEventListener("click", () => {
        const role = latestAnalysisData?.target_role || "software_engineer";
        const mockRoleSelect = document.getElementById("mockRoleSelect");
        if (mockRoleSelect) mockRoleSelect.value = role;
        document.getElementById("navMock")?.click();
    });
}


// ================================
// MODULE 1: JOB RECOMMENDATIONS
// ================================
function setupJobRecommendations() {
    const filter = document.getElementById("jobRoleFilter");
    filter?.addEventListener("change", () => loadJobs(filter.value));
}

async function loadJobs(role = "software_engineer") {
    const container = document.getElementById("jobsContainer");
    if (!container) return;
    container.innerHTML = '<div style="grid-column: 1/-1; padding: 30px; text-align: center; color: var(--text-muted);">Fetching matching job openings...</div>';

    try {
        const res = await fetch(`${API_BASE_URL}/career/jobs?role=${encodeURIComponent(role)}`);
        const data = await res.json();

        if (res.ok && data.jobs) {
            container.innerHTML = "";
            data.jobs.forEach(job => {
                const card = document.createElement("div");
                card.className = "result-card";
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div>
                            <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-weight: 700; padding: 4px 10px; border-radius: 12px;">${job.match} Skill Match</span>
                            <h3 style="margin: 10px 0 4px; font-size: 18px;">${job.title}</h3>
                            <p style="color: var(--primary-light); font-weight: 600; font-size: 14px; margin-bottom: 4px;">🏢 ${job.company}</p>
                            <p style="color: var(--text-subtle); font-size: 13px;">📍 ${job.location}</p>
                        </div>
                        <span style="font-size: 12px; background: rgba(255,255,255,0.06); padding: 4px 10px; border-radius: 8px; color: var(--text-muted);">${job.portal}</span>
                    </div>
                    <a href="${job.apply_url}" target="_blank" class="primary-button" style="display: inline-flex; width: 100%; justify-content: center; margin-top: 14px; text-decoration: none;">
                        <span>Apply on ${job.portal}</span>
                        <span>↗</span>
                    </a>
                `;
                container.appendChild(card);
            });
        }
    } catch (e) {
        container.innerHTML = '<div style="grid-column: 1/-1; color: #fca5a5;">Could not fetch job recommendations.</div>';
    }
}

// ================================
// MODULE 2: CAREER ROADMAP & OFFICIAL WEBSITES
// ================================
function setupRoadmap() {
    const filter = document.getElementById("roadmapRoleFilter");
    filter?.addEventListener("change", () => loadRoadmap(filter.value));
}

async function loadRoadmap(role = "software_engineer") {
    const container = document.getElementById("roadmapContainer");
    if (!container) return;
    container.innerHTML = '<div style="padding: 30px; text-align: center; color: var(--text-muted);">Loading career progression roadmap...</div>';

    try {
        const res = await fetch(`${API_BASE_URL}/career/roadmap?role=${encodeURIComponent(role)}`);
        const data = await res.json();

        if (res.ok && data.roadmap) {
            const r = data.roadmap;
            let html = `
                <div class="result-card" style="margin-bottom: 24px;">
                    <h3 style="font-size: 22px; margin-bottom: 6px;">${r.title}</h3>
                    <p style="color: var(--text-muted); font-size: 14px;">${r.description}</p>
                </div>
            `;

            r.phases.forEach((phase, idx) => {
                html += `
                    <div class="result-card" style="margin-bottom: 20px; border-left: 4px solid var(--primary);">
                        <h4 style="font-size: 17px; font-weight: 800; color: var(--primary-light); margin-bottom: 12px;">${phase.phase}</h4>
                        <div style="margin-bottom: 16px;">
                            <strong style="font-size: 13px; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.5px;">Core Competencies to Master:</strong>
                            <ul style="margin-top: 8px; padding-left: 20px;">
                                ${phase.topics.map(t => `<li style="margin-bottom: 6px; font-size: 14px; color: var(--text-main);">${t}</li>`).join("")}
                            </ul>
                        </div>
                        <div>
                            <strong style="font-size: 13px; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.5px;">Recommended Official Resources & Websites:</strong>
                            <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">
                                ${phase.resources.map(res => `
                                    <a href="${res.url}" target="_blank" class="nav-btn-secondary" style="font-size: 13px; display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px;">
                                        <span>🌐 ${res.name}</span>
                                        <span>↗</span>
                                    </a>
                                `).join("")}
                            </div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
    } catch (e) {
        container.innerHTML = '<div style="color: #fca5a5;">Could not load roadmap.</div>';
    }
}

// ================================
// MODULE 3: AI MOCK INTERVIEW AGENT (VOICE & NLP)
// ================================
let speechRecognitionInstance = null;
let isRecordingVoice = false;

function setupMockInterview() {
    const roleSelect = document.getElementById("mockRoleSelect");
    roleSelect?.addEventListener("change", () => loadMockQuestions(roleSelect.value));

    const nextBtn = document.getElementById("nextMockQuestionBtn");
    nextBtn?.addEventListener("click", () => {
        if (currentMockQuestions.length > 0) {
            currentMockIndex = (currentMockIndex + 1) % currentMockQuestions.length;
            displayMockQuestion();
        }
    });

    // Voice Readout (Text-to-Speech)
    const voiceToggleBtn = document.getElementById("voiceInterviewerToggle");
    voiceToggleBtn?.addEventListener("click", () => {
        if (currentMockQuestions.length === 0) return;
        const q = currentMockQuestions[currentMockIndex];
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(q.question);
            utterance.rate = 0.95;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        } else {
            alert("Speech synthesis is not supported on this browser.");
        }
    });

    // Voice Recognition (Speech-to-Text)
    const micRecordBtn = document.getElementById("micRecordBtn");
    const micIcon = document.getElementById("micIcon");
    const micLabel = document.getElementById("micLabel");
    const voiceStatus = document.getElementById("voiceAgentStatus");
    const answerInput = document.getElementById("mockAnswerInput");

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        speechRecognitionInstance = new SpeechRecognition();
        speechRecognitionInstance.continuous = true;
        speechRecognitionInstance.interimResults = true;
        speechRecognitionInstance.lang = "en-US";

        speechRecognitionInstance.onresult = (event) => {
            let transcript = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            if (answerInput) {
                answerInput.value = (answerInput.value ? answerInput.value + " " : "") + transcript;
            }
        };

        speechRecognitionInstance.onerror = (e) => {
            console.warn("Speech recognition error:", e);
            stopVoiceRecording();
        };

        speechRecognitionInstance.onend = () => {
            if (isRecordingVoice) {
                stopVoiceRecording();
            }
        };
    }

    function startVoiceRecording() {
        if (!speechRecognitionInstance) {
            alert("Speech recognition is not supported by your browser. Please use Google Chrome or Microsoft Edge.");
            return;
        }
        isRecordingVoice = true;
        speechRecognitionInstance.start();
        if (micIcon) micIcon.textContent = "⏹️";
        if (micLabel) micLabel.textContent = "Stop Recording";
        if (voiceStatus) voiceStatus.style.display = "inline";
    }

    function stopVoiceRecording() {
        isRecordingVoice = false;
        if (speechRecognitionInstance) speechRecognitionInstance.stop();
        if (micIcon) micIcon.textContent = "🎙️";
        if (micLabel) micLabel.textContent = "Speak Answer";
        if (voiceStatus) voiceStatus.style.display = "none";
    }

    micRecordBtn?.addEventListener("click", () => {
        if (!isRecordingVoice) startVoiceRecording();
        else stopVoiceRecording();
    });

    const submitBtn = document.getElementById("submitMockAnswerBtn");
    submitBtn?.addEventListener("click", async () => {
        if (isRecordingVoice) stopVoiceRecording();

        const input = document.getElementById("mockAnswerInput");
        const answer = input?.value.trim() || "";
        const resultBox = document.getElementById("mockEvaluationResult");

        if (answer.length < 15) {
            alert("Please provide a more detailed answer for thorough AI evaluation (at least 15 characters).");
            return;
        }

        const role = roleSelect?.value || "software_engineer";
        const currentQ = currentMockQuestions[currentMockIndex];

        submitBtn.disabled = true;
        submitBtn.innerHTML = "<span>Analyzing Answer & Cadence...</span> <span>⏳</span>";

        try {
            const res = await fetch(`${API_BASE_URL}/career/interview/evaluate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    role: role,
                    question_id: currentQ.id,
                    user_answer: answer
                })
            });

            const data = await res.json();
            if (res.ok && resultBox) {
                resultBox.style.display = "block";
                resultBox.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div>
                            <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: var(--primary-light); font-weight: 700; padding: 4px 10px; border-radius: 12px;">AI Evaluation Score</span>
                            <h2 style="font-size: 32px; font-weight: 800; margin-top: 6px; color: ${data.score >= 80 ? '#34d399' : (data.score >= 60 ? '#fbbf24' : '#f87171')};">${data.score}/100 <span style="font-size: 16px; color: var(--text-muted);">(${data.rating})</span></h2>
                        </div>
                    </div>
                    <p style="font-size: 14px; line-height: 1.6; margin-bottom: 14px; color: var(--text-main); font-weight: 500;">${data.feedback}</p>
                    <div style="margin-top: 12px;">
                        <strong style="font-size: 12px; color: var(--text-subtle); text-transform: uppercase;">Keywords Detected in Your Answer:</strong>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
                            ${data.keywords_matched.length > 0 ? data.keywords_matched.map(k => `<span class="skill-tag" style="padding: 4px 10px; font-size: 12px;">✓ ${k}</span>`).join("") : '<span style="color: var(--text-subtle); font-size: 13px;">None matched</span>'}
                        </div>
                    </div>
                `;

                // Read AI feedback voice response
                if ('speechSynthesis' in window) {
                    const evalUtterance = new SpeechSynthesisUtterance(`Your evaluation score is ${data.score} out of 100. ${data.feedback}`);
                    evalUtterance.rate = 1.0;
                    window.speechSynthesis.speak(evalUtterance);
                }
            }
        } catch (e) {
            alert("Failed to evaluate answer.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>Evaluate with AI Agent</span> <span>🤖</span>";
        }
    });
}

async function loadMockQuestions(role = "software_engineer") {
    try {
        const res = await fetch(`${API_BASE_URL}/career/interview/questions?role=${encodeURIComponent(role)}`);
        const data = await res.json();
        if (res.ok && data.questions) {
            currentMockQuestions = data.questions;
            currentMockIndex = 0;
            displayMockQuestion();
        }
    } catch (e) {
        console.error(e);
    }
}

function displayMockQuestion() {
    if (currentMockQuestions.length === 0) return;
    const q = currentMockQuestions[currentMockIndex];
    const categoryBadge = document.getElementById("mockCategoryBadge");
    const questionText = document.getElementById("mockQuestionText");
    const answerInput = document.getElementById("mockAnswerInput");
    const resultBox = document.getElementById("mockEvaluationResult");

    if (categoryBadge) categoryBadge.textContent = `${q.category} • Question ${currentMockIndex + 1}/${currentMockQuestions.length}`;
    if (questionText) questionText.textContent = q.question;
    if (answerInput) answerInput.value = "";
    if (resultBox) resultBox.style.display = "none";
}

// ================================
// MODULE 4: APTITUDE & CORE ASSESSMENT
// ================================
function setupAptitudeTest() {
    const filter = document.getElementById("aptitudeRoleFilter");
    filter?.addEventListener("change", () => loadAptitudeTest(filter.value));
}

async function loadAptitudeTest(role = "software_engineer") {
    const container = document.getElementById("aptitudeContainer");
    if (!container) return;
    
    // Auto-sync filter if parameter passed
    const filter = document.getElementById("aptitudeRoleFilter");
    if (filter && filter.value !== role) filter.value = role;

    container.innerHTML = '<div style="padding: 30px; text-align: center; color: var(--text-muted);">Loading role-tailored assessment test questions...</div>';

    try {
        const res = await fetch(`${API_BASE_URL}/career/aptitude?role=${encodeURIComponent(role)}`);
        const data = await res.json();

        if (res.ok && data.questions) {
            aptitudeQuestionsData = data.questions;
            userAptitudeAnswers = {};

            let html = `
                <div class="result-card" style="margin-bottom: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 20px; margin-bottom: 4px;">Institutional Readiness Assessment (${role.replace('_', ' ').toUpperCase()})</h3>
                            <p style="color: var(--text-muted); font-size: 14px;">Tailored technical reasoning, CS architecture, and domain problems frequently asked in tier-1 corporate exams.</p>
                        </div>
                        <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: var(--primary-light); font-weight: 700; padding: 6px 14px; border-radius: 20px;">5 Questions</span>
                    </div>
                </div>
            `;

            data.questions.forEach((q, idx) => {
                html += `
                    <div class="result-card" style="margin-bottom: 20px;">
                        <span class="badge" style="background: rgba(255, 255, 255, 0.08); color: var(--accent); font-weight: 700; padding: 4px 10px; border-radius: 12px; font-size: 12px;">${q.category}</span>
                        <h4 style="font-size: 16px; font-weight: 700; margin: 12px 0 16px; line-height: 1.5;">${idx + 1}. ${q.question}</h4>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            ${q.options.map((opt, optIdx) => `
                                <label style="display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: rgba(9, 13, 22, 0.6); border: 1px solid var(--border-color); border-radius: 10px; cursor: pointer; transition: 0.2s;" class="apt-option-label" data-qid="${q.id}" data-opt="${optIdx}">
                                    <input type="radio" name="apt_q_${q.id}" value="${optIdx}" onchange="selectAptAnswer(${q.id}, ${optIdx})" style="accent-color: var(--primary);">
                                    <span style="font-size: 14px;">${opt}</span>
                                </label>
                            `).join("")}
                        </div>
                        <div id="aptExpl_${q.id}" style="display: none; margin-top: 14px; padding: 12px 16px; border-radius: 10px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); font-size: 13px; color: #a7f3d0;">
                            <strong>Explanation:</strong> ${q.explanation}
                        </div>
                    </div>
                `;
            });

            html += `
                <div style="text-align: center; margin-top: 30px;">
                    <button class="primary-button" onclick="submitAptitudeTest()" style="padding: 14px 40px;">
                        <span>Submit & Calculate Score</span>
                        <span>📊</span>
                    </button>
                    <div id="aptitudeScoreBanner" style="display: none; margin-top: 24px; padding: 24px; border-radius: 18px; background: var(--bg-card); border: 1px solid var(--border-color);"></div>
                </div>
            `;

            container.innerHTML = html;
        }
    } catch (e) {
        container.innerHTML = '<div style="color: #fca5a5;">Could not load aptitude test.</div>';
    }
}

window.selectAptAnswer = function(qId, optIdx) {
    userAptitudeAnswers[qId] = optIdx;
};

window.submitAptitudeTest = function() {
    let score = 0;
    aptitudeQuestionsData.forEach(q => {
        const chosen = userAptitudeAnswers[q.id];
        const explBox = document.getElementById(`aptExpl_${q.id}`);
        if (explBox) explBox.style.display = "block";

        if (chosen === q.answer_index) {
            score++;
        }
    });

    const percent = Math.round((score / aptitudeQuestionsData.length) * 100);
    const banner = document.getElementById("aptitudeScoreBanner");
    if (banner) {
        banner.style.display = "block";
        banner.innerHTML = `
            <h3 style="font-size: 24px; font-weight: 800; margin-bottom: 8px;">Assessment Result: ${score} / ${aptitudeQuestionsData.length} Correct (${percent}%)</h3>
            <p style="color: var(--text-muted); font-size: 14px;">${percent >= 80 ? '🌟 Exceptional aptitude & CS fundamentals!' : (percent >= 60 ? '👍 Solid performance! Review the explanations above for missed questions.' : '⚠️ Practice quantitative & core algorithmic reasoning using the recommended roadmaps.')}</p>
        `;
        banner.scrollIntoView({ behavior: "smooth" });
    }
};

// ================================
// MODULE 5: RESUME BUILDING BLUEPRINTS (DYNAMIC + UNIVERSAL)
// ================================
function setupResumeTips() {
    // Loaded on view switch
}

async function loadResumeTips() {
    const container = document.getElementById("tipsContainer");
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE_URL}/career/tips`);
        const data = await res.json();

        if (res.ok && data.tips) {
            container.innerHTML = "";

            // 1. If user has analyzed a resume, inject Candidate-Specific Diagnostic Analysis Cards first
            if (latestAnalysisData) {
                const roleFormatted = (latestAnalysisData.target_role || "software_engineer").replace("_", " ").toUpperCase();
                
                const customCard = document.createElement("div");
                customCard.className = "result-card";
                customCard.style.gridColumn = "1 / -1";
                customCard.style.border = "1px solid rgba(16, 185, 129, 0.4)";
                customCard.style.background = "linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(9, 13, 22, 0.9) 100%)";
                
                let missingListHtml = "";
                if (latestAnalysisData.missing_skills && latestAnalysisData.missing_skills.length > 0) {
                    missingListHtml = latestAnalysisData.missing_skills.map(s => `<span class="skill-tag" style="background: rgba(239, 68, 68, 0.15); color: #fca5a5; border-color: rgba(239, 68, 68, 0.4);">+ ${s}</span>`).join(" ");
                } else {
                    missingListHtml = '<span style="color: #86efac; font-weight: 700;">✓ 100% Core Competency Match! No missing keywords identified.</span>';
                }

                let suggestionsHtml = "";
                if (latestAnalysisData.suggestions && latestAnalysisData.suggestions.length > 0) {
                    suggestionsHtml = latestAnalysisData.suggestions.map(s => `<li style="margin-bottom: 6px; color: #cbd5e1;">${s}</li>`).join("");
                }

                customCard.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
                        <div>
                            <span class="badge" style="background: rgba(16, 185, 129, 0.25); color: #86efac; font-weight: 800; padding: 4px 12px; border-radius: 20px;">🎯 LIVE RESUME DIAGNOSTICS</span>
                            <h3 style="font-size: 20px; font-weight: 800; margin: 10px 0 4px; color: #ffffff;">Personalized Optimization for: ${latestAnalysisData.filename || 'Your Uploaded Resume'}</h3>
                            <p style="color: var(--text-muted); font-size: 14px;">Evaluated Profile: <strong>${roleFormatted}</strong> | Current ATS Index: <strong style="color:${latestAnalysisData.ats_score >= 80 ? '#34d399' : '#fbbf24'};">${latestAnalysisData.ats_score} / 100</strong></p>
                        </div>
                        <button onclick="document.getElementById('navDashboard')?.click(); document.getElementById('rebuild100Btn')?.click();" class="primary-button" style="margin: 0; padding: 10px 20px; font-size: 13px;">
                            <span>⚡ 1-Click Auto-Fix to 100%</span>
                        </button>
                    </div>

                    <div style="margin-bottom: 16px;">
                        <strong style="font-size: 13px; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.5px;">Target Framework Gaps to Inject into Experience:</strong>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;">
                            ${missingListHtml}
                        </div>
                    </div>

                    <div>
                        <strong style="font-size: 13px; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.5px;">Algorithmic Recommendations for Your Document:</strong>
                        <ul style="margin-top: 8px; padding-left: 20px; font-size: 14px;">
                            ${suggestionsHtml}
                        </ul>
                    </div>
                `;
                container.appendChild(customCard);
            }

            // 2. Render Universal Elite Resume Blueprints
            data.tips.forEach(tip => {
                const card = document.createElement("div");
                card.className = "result-card";
                card.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                        <span style="font-size: 24px;">💡</span>
                        <h3 style="font-size: 18px; margin: 0; color: #ffffff;">${tip.title}</h3>
                    </div>
                    <p style="color: var(--text-muted); font-size: 14px; line-height: 1.6; margin-bottom: 16px;">${tip.summary}</p>
                    <div style="background: rgba(9, 13, 22, 0.85); padding: 14px; border-radius: 12px; border: 1px solid var(--border-color); font-family: var(--font-mono); font-size: 12px; color: #e0e7ff; line-height: 1.6; white-space: pre-wrap;">${tip.example}</div>
                `;
                container.appendChild(card);
            });
        }
    } catch (e) {
        container.innerHTML = '<div style="color: #fca5a5;">Could not load resume tips.</div>';
    }
}

// ================================
// RESUME HISTORY TABLE
// ================================
function setupHistory() {}

async function loadHistoryTable() {
    const tbody = document.getElementById("historyTableBody");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Loading evaluation history...</td></tr>';

    try {
        const res = await fetch(`${API_BASE_URL}/history?email=${encodeURIComponent(currentUser.email)}`);
        const data = await res.json();

        if (res.ok && data.history && data.history.length > 0) {
            tbody.innerHTML = "";
            data.history.forEach(item => {
                const tr = document.createElement("tr");

                let scoreClass = "score-low";
                if (item.ats_score >= 80) scoreClass = "score-high";
                else if (item.ats_score >= 60) scoreClass = "score-med";

                const dateFormatted = item.analyzed_at ? item.analyzed_at.substring(0, 16).replace("T", " ") : "Recent";
                const roleFormatted = (item.target_role || "general").replace("_", " ").toUpperCase();

                tr.innerHTML = `
                    <td>${dateFormatted}</td>
                    <td><strong>${item.filename}</strong></td>
                    <td>${roleFormatted}</td>
                    <td><span class="score-badge ${scoreClass}">${item.ats_score} / 100</span></td>
                    <td>${item.skills ? item.skills.length : 0} Skills</td>
                    <td>
                        <button class="btn-sm" onclick="deleteHistoryItem(${item.id})">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding: 30px; opacity: 0.6;">No resumes analyzed yet. Upload a resume to view reports here.</td></tr>';
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center" style="color: #fca5a5;">Could not fetch history from backend.</td></tr>';
    }
}

window.deleteHistoryItem = async function(id) {
    if (!confirm("Are you sure you want to delete this evaluation report?")) return;
    try {
        const res = await fetch(`${API_BASE_URL}/history/${id}?email=${encodeURIComponent(currentUser.email)}`, {
            method: "DELETE"
        });
        if (res.ok) {
            loadHistoryTable();
            fetchDashboardStats();
        }
    } catch (e) {
        alert("Failed to delete record.");
    }
};

// ================================
// PROFILE VIEW & UPDATE
// ================================
function setupProfile() {
    const profileForm = document.getElementById("profileForm");
    profileForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const newName = document.getElementById("profileNameInput").value.trim();
        const newTitle = document.getElementById("profileTitleInput").value.trim();
        const linkedinUrl = document.getElementById("profileLinkedInInput")?.value.trim() || "";
        const githubUrl = document.getElementById("profileGithubInput")?.value.trim() || "";
        const profileMsg = document.getElementById("profileMessage");

        try {
            const res = await fetch(`${API_BASE_URL}/user/profile/update?email=${encodeURIComponent(currentUser.email)}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: newName, title: newTitle })
            });

            if (res.ok) {
                currentUser.name = newName;
                currentUser.title = newTitle;
                currentUser.linkedin = linkedinUrl;
                currentUser.github = githubUrl;

                localStorage.setItem("userName", newName);
                localStorage.setItem("userTitle", newTitle);
                localStorage.setItem("userLinkedIn", linkedinUrl);
                localStorage.setItem("userGithub", githubUrl);

                initUserHeader();
                loadProfileView();

                if (profileMsg) {
                    profileMsg.textContent = "✅ Profile & portal links connected successfully!";
                    profileMsg.style.color = "#86efac";
                }
            }
        } catch (e) {
            if (profileMsg) {
                profileMsg.textContent = "❌ Failed to update profile.";
                profileMsg.style.color = "#fca5a5";
            }
        }
    });
}

async function loadProfileView() {
    const profileNameDisplay = document.getElementById("profileNameDisplay");
    const profileEmailDisplay = document.getElementById("profileEmailDisplay");
    const profileLargeAvatar = document.getElementById("profileLargeAvatar");
    const profileNameInput = document.getElementById("profileNameInput");
    const profileTitleInput = document.getElementById("profileTitleInput");
    const profileEmailInput = document.getElementById("profileEmailInput");
    const profileLinkedInInput = document.getElementById("profileLinkedInInput");
    const profileGithubInput = document.getElementById("profileGithubInput");

    const savedLinkedIn = localStorage.getItem("userLinkedIn") || "";
    const savedGithub = localStorage.getItem("userGithub") || "";

    if (profileNameDisplay) profileNameDisplay.textContent = currentUser.name;
    if (profileEmailDisplay) profileEmailDisplay.textContent = currentUser.email;
    if (profileLargeAvatar) profileLargeAvatar.textContent = currentUser.name.charAt(0).toUpperCase();

    if (profileNameInput) profileNameInput.value = currentUser.name;
    if (profileTitleInput) profileTitleInput.value = currentUser.title;
    if (profileEmailInput) profileEmailInput.value = currentUser.email;
    if (profileLinkedInInput) profileLinkedInInput.value = savedLinkedIn;
    if (profileGithubInput) profileGithubInput.value = savedGithub;
}

// ================================
// DASHBOARD STATS REFRESH
// ================================
async function fetchDashboardStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/user/profile?email=${encodeURIComponent(currentUser.email)}`);
        const data = await res.json();
        if (res.ok) {
            const resumeStat = document.getElementById("resumeStat");
            if (resumeStat) resumeStat.textContent = data.total_resumes || 0;
        }
    } catch (e) {
        // Fallback or silent
    }
}

// ================================
// LOGOUT
// ================================
function setupLogout() {
    const logoutButton = document.getElementById("logoutButton");
    logoutButton?.addEventListener("click", () => {
        localStorage.removeItem("isLoggedIn");
        localStorage.removeItem("userEmail");
        localStorage.removeItem("userName");
        localStorage.removeItem("userTitle");
        window.location.href = "login.html";
    });
}