// ==UserScript==
// @name         Tsync
// @namespace    http://tampermonkey.net/
// @version      2025-06-19
// @description  Convinient way to upload files to tsync
// @author       CryptoCore
// @match        https://moodle.rwth-aachen.de/mod/quiz/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=rwth-aachen.de
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_addStyle
// ==/UserScript==

(async function() {
    'use strict';
    function updateInputs() {
        inps.forEach(inp => {
            inp.setAttribute('value', inp.value);
            if (inp.getAttribute("type") == "checkbox" || inp.getAttribute("type") == "radio") {
                inp.setAttribute('value', inp.checked ? "1" : "0");
                if (inp.checked) {
                    inp.setAttribute('checked', 'checked');
                } else {
                    inp.removeAttribute('checked');
                }
            }
        });
    }

    function uploadPage() {
        if (!apiKey) {
            error.textContent = "No api key specified.";
        }
        updateInputs();
        let fullHTML = document.body.outerHTML;

        GM_xmlhttpRequest({
            method: "POST",
            url: url + "/api/upload",
            headers: {
                "Content-Type": "application/text",
                "tsync-api-key": apiKey,
            },
            data: fullHTML,
            onload: function(response) {
                if (response.status == 200) {
                    if (!autoUpdate) {
                        info.textContent = "Uploaded test.";
                        error.textContent = "";
                    }
                } else {
                    error.textContent = "Failed to upload test: " + response.statusText;
                }
            },
            onerror: function(error) {
                error.textContent = "Failed to upload test.";
            }
        });
    }

    function getCMID() {
        return new URL(location.href).searchParams.get('cmid');
    }

    function downloadSolutions() {
        GM_xmlhttpRequest({
            method: "GET",
            url: url + `/api/solutions/${getCMID()}`,
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

    const url = "{{ url }}";

    let apiKey = await GM_getValue("apikey", null);
    let autoUpdate = await GM_getValue("autoUpdate", false);
    let lastUpdate = 0;

    let inps = document.querySelector('form').querySelectorAll('input:not([type="hidden"]):not([type="submit"])');

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

    // event handling
    inps.forEach(inp => {
        inp.addEventListener('input', valueChange);
    });
})();
