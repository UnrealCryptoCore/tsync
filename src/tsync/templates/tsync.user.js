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
    const url = "{{ url }}";

    let apiKey = await GM_getValue("apikey", null);
    let autoUpdate = await GM_getValue("autoUpdate", false);
    let lastUpdate = 0;

    let inps = document.querySelector('form').querySelectorAll('input:not([type="hidden"]):not([type="submit"])');

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
                        info.textContent = "everything up to date";
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
                    console.log(response.responseText);
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
            const inp = document.getElementById(key);
            const parent = inp.parentNode;
            const solE = document.createElement('div');
            solE.innerHTML = solutions[key];
            parent.appendChild(solE);
        }
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

    GM_addStyle(`
        .tsync-main-box {
            z-index: 9999;
            position: fixed;
            bottom: 1rem;
            left: 1rem;
            background-color: #3c3c3c;
            padding: 0.5rem;
            border-radius: 0.3rem;
            color: white;
            box-shadow: 5px 5px 5px black;
        }

        .tsync-btn {
            background-color: #3a7cff;
            border-radius: 0.4rem;
            border-style: hidden;
            margin: 0.3rem;
            display: block;
            width: 12rem;
            color: white;
        }
    `);

    // ui
    const box = document.createElement('div');
    box.classList.add('tsync-main-box');
    const title = document.createElement('h3');
    title.textContent = "Tsync";
    box.appendChild(title);

    //const btnRow = document.createElement('div');

    const updateBtn = document.createElement('button');
    updateBtn.textContent = "Upload";
    updateBtn.classList.add('tsync-btn');
    updateBtn.addEventListener('click', uploadPage);
    box.appendChild(updateBtn);

    const keyBtn = document.createElement('button');
    keyBtn.textContent = "API Key";
    keyBtn.classList.add('tsync-btn');
    keyBtn.addEventListener('click', updateApiKey);
    box.appendChild(keyBtn);

    const downloadBtn = document.createElement('button');
    downloadBtn.textContent = "Show Solution";
    downloadBtn.classList.add('tsync-btn');
    downloadBtn.addEventListener('click', downloadSolutions);
    box.appendChild(downloadBtn);


    const updateBox = document.createElement('div');
    updateBox.innerHTML = '<span>auto upload</span>';
    updateBox.style.display = 'flex';
    updateBox.style.justifyContent = 'space-between';
    updateBox.addEventListener('click', updateAutoUpdate);

    const updateBoxCheck = document.createElement('input');
    updateBoxCheck.type = 'checkbox';
    updateBoxCheck.checked = autoUpdate;
    updateBox.appendChild(updateBoxCheck);

    box.appendChild(updateBox);


    const info = document.createElement('div');
    info.textContent = "";
    box.appendChild(info);

    const error = document.createElement('div');
    error.textContent = "";
    error.style.color = "red";
    box.appendChild(error);

    document.body.appendChild(box);

    // event handling
    inps.forEach(inp => {
        inp.addEventListener('input', valueChange);
    });
})();
