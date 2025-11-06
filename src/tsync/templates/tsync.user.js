// ==UserScript==
// @name         TSync
// @namespace    http://tampermonkey.net/
// @version      2025-11-06
// @description  Convenient way to upload files to tsync
// @author       CryptoCore
// @match        https://moodle.rwth-aachen.de/mod/quiz/*
// @match        {{ url }}/*
// @icon         {{ url }}/static/favicon-rwth.png
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_addStyle
// ==/UserScript==



async function handleTsync(url, apiKey) {
    if (apiKey !== null) {
        return;
    }
    const res = await fetch(`${url}/apikey-get`);
    if (res.ok) {
        const data = await res.json()
        apiKey = data.key;
        GM_setValue("apikey", apiKey);
    }
}

async function handleMoodle(url, apiKey) {
    function getInputs() {
        return document.querySelector('form').querySelectorAll('input:not([type="hidden"]):not([type="submit"])');
    }

    function updateInputs() {
        getInputs().forEach(inp => {
            if (inp.getAttribute("type") == "checkbox" || inp.getAttribute("type") == "radio") {
                if (inp.checked) {
                    inp.setAttribute('checked', 'checked');
                } else {
                    inp.removeAttribute('checked');
                }
            } else {
                inp.setAttribute('value', inp.value);
            }
        });
    }

    function uploadPage() {
        if (!apiKey) {
            error.textContent = "No api key specified.";
        }
        updateInputs();
        let fullHTML = document.body.outerHTML;

        return new Promise((resolve, _) =>
            GM_xmlhttpRequest({
                method: "POST",
                url: url + "/api/upload",
                headers: {
                    "Content-Type": "application/text",
                    "tsync-api-key": apiKey,
                },
                data: fullHTML,
                onload: function(res) {
                    if (res.status == 200) {
                        if (!autoUpdate) {
                            info.textContent = "Uploaded test.";
                        }
                        error.textContent = "";
                        didUpload = true;
                    } else if (res.status === 401) {
                        error.textContent = "Invalid api-key.";
                    } else {
                        error.textContent = "Failed to upload test.";
                    }
                    resolve(true);
                },
                onerror: function(error) {
                    error.textContent = "Failed to upload test.";
                    resolve(false);
                }
            })
        );


    }

    function getCMID() {
        let cmid = new URL(location.href).searchParams.get('cmid');
        if (cmid) {
            return cmid;
        }
        // backup if url does not exist
        document.getElementsByTagName('body').classList.forEach((c) => {
            if (c.startsWith('cmid')) {
                return c.split('-')[1];
            }
        });
        return null;
    }

    async function downloadSolutions() {
        if (!didUpload) {
            const res = await uploadPage();
            if (!res) {
                return;
            }
        }
        const cmid = getCMID();
        if (cmid == null) {
            error.textContent = "Could not find cmid.";
            return;
        }
        GM_xmlhttpRequest({
            method: "GET",
            url: url + `/api/solutions/${cmid}`,
            headers: {
                "Content-Type": "application/text",
                "tsync-api-key": apiKey,
            },
            onload: function(response) {
                if (response.status == 200) {
                    showSolutions(JSON.parse(response.responseText));
                } else {
                    error.textContent = "Failed to upload test: " + response.statusText;
                }
            },
            onerror: function(error) {
                error.textContent = "Failed to upload test.";
            }
        });
    }

    function showSolutions(solutions) {
        for (const key in solutions) {
            const id = `tsync-solution-${key}`;
            const inp = document.getElementById(key);
            let solE = document.getElementById(id);
            if (!solE) {
                const parent = inp.parentNode;
                solE = document.createElement('div');
                solE.id = id;
                parent.appendChild(solE);
            }
            solE.innerHTML = solutions[key];
        }
        document.getElementsByClassName('tsync-ai-btn').forEach((aibtn) => {
            aibtn.addEventListener('click', () => askai(aibtn.id.split("-").at(-1)));
        });
    }

    function requestFailed(errorMsg, interval) {
        error.textContent = errorMsg;
        document.getElementsByClassName('tsync-ai-btn').forEach((btn) => {
            btn.classList.remove('loading');
        });
        clearInterval(interval);
        info.textContent = "";
    }

    function askai(id) {
        document.getElementsByClassName('tsync-ai-btn').forEach((btn) => {
            btn.classList.add('loading');
        });

        let i = 0;
        let j = 1;
        info.textContent = waitingMessages[0];
        const interval = setInterval(() => {
            if (j == 0) {
                info.textContent = waitingMessages[i];
            } else {
                info.textContent += ".";
            }
            j++;
            if (j == 5) {
                j = 0;
                i++;
            }
            if (i == waitingMessages.length) {
                clearInterval(interval);
                info.textContent = "";
            }
        }, 500);
        GM_xmlhttpRequest({
            method: "GET",
            url: url + `/api/aianswer/${id}`,
            headers: {
                "tsync-api-key": apiKey,
            },
            timeout: 80000,
            onload: function(_) {
                downloadSolutions();
                clearInterval(interval);
                info.textContent = "";
            },
            onerror: function(error) {
                requestFailed(`${error.responseText}  ${error.status}`, interval);
            },
            ontimeout: function() {
                requestFailed("AI response timed out. Try again later.", interval);
            }
        });

    }

    function updateApiKey() {
        apiKey = prompt("enter api key");
        GM_setValue("apikey", apiKey);
    }

    function updateAutoUpdate() {
        autoUpdate = !autoUpdate;
        updateBoxCheck.checked = autoUpdate;
        if (autoUpdate) {
            info.textContent = "";
        }
        GM_setValue("autoUpdate", autoUpdate);
    }

    function valueChange() {
        if (autoUpdate) {
            let newLastUpdate = Date.now();
            setTimeout(() => {
                if (Date.now() - lastUpdate > 1000) {
                    uploadPage();
                }
            }, 1200);

            lastUpdate = newLastUpdate;
        } else {
            info.textContent = "unsaved changes";
        }
    }


    GM_addStyle(`{{ styles }}`);

    let autoUpdate = await GM_getValue("autoUpdate", true);
    let lastUpdate = 0;
    let didUpload = false;

    let inps = getInputs();

    const waitingMessages = [
        "Sending request",
        "Analyzing",
        "Thinking",
        "Consulting the oracle",
        "Synthesizing insights",
        "Almost there"
    ];

    // ui
    const box = document.createElement('div');
    box.classList.add('tsync-main-box');
    const title = document.createElement('h3');
    title.textContent = "Tsync";
    box.appendChild(title);

    const updateBtn = document.createElement('button');
    updateBtn.textContent = "Upload";
    updateBtn.classList.add('tsync-btn');
    updateBtn.addEventListener('click', uploadPage);
    box.appendChild(updateBtn);

    const downloadBtn = document.createElement('button');
    downloadBtn.textContent = "Show Solution";
    downloadBtn.classList.add('tsync-btn');
    downloadBtn.addEventListener('click', downloadSolutions);
    box.appendChild(downloadBtn);

    const keyBtn = document.createElement('button');
    keyBtn.textContent = "API Key";
    keyBtn.classList.add('tsync-btn');
    keyBtn.addEventListener('click', updateApiKey);
    box.appendChild(keyBtn);

    const textBox = document.createElement('div');
    textBox.className = "text-box";

    const updateBox = document.createElement('div');
    updateBox.className = "update-box";
    updateBox.innerHTML = '<span>auto upload</span>';
    updateBox.style.display = 'flex';
    updateBox.style.justifyContent = 'space-between';
    updateBox.addEventListener('click', updateAutoUpdate);

    const updateBoxCheck = document.createElement('input');
    updateBoxCheck.type = 'checkbox';
    updateBoxCheck.checked = autoUpdate;
    updateBox.appendChild(updateBoxCheck);

    textBox.appendChild(updateBox);


    const info = document.createElement('div');
    info.textContent = "";
    textBox.appendChild(info);

    const error = document.createElement('div');
    error.textContent = "";
    error.style.color = "red";
    textBox.appendChild(error);

    box.appendChild(textBox);

    document.body.appendChild(box);

    // check for user input
    inps.forEach(inp => {
        inp.addEventListener('input', valueChange);
    });

}

(async function() {
    'use strict';

    const url = "{{ url }}";

    const apiKey = await GM_getValue("apikey", null);

    if (window.location.href.startsWith(url)) {
        handleTsync(url, apiKey);
    } else {
        handleMoodle(url, apiKey);
    }
})();
