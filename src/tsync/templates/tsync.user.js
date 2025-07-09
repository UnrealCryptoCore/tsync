// ==UserScript==
// @name         Tsync
// @namespace    http://tampermonkey.net/
// @version      2025-06-19
// @description  Convinient way to upload files to tsync
// @author       You
// @match        https://moodle.rwth-aachen.de/mod/quiz/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=rwth-aachen.de
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// ==/UserScript==

(async function() {
    'use strict';
    const url = "{{ url }}";

    let apiKey = await GM_getValue("apikey", null);
    let autoUpdate = await GM_getValue("autoUpdate", false);
    let lastUpdate = 0;

    let inps = document.getElementById('responseform').querySelectorAll('input:not([type="hidden"]):not([type="submit"])');

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

    function tsync() {
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
                    }
                }
                else {
                    error.textContent = "Failed to upload test: " + response.statusText;
                }
            },
            onerror: function(error) {
                error.textContent = "Failed to upload test.";
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
                    tsync();
                }
            }, 1200);

            lastUpdate = newLastUpdate;
        } else {
            info.textContent = "unsaved changes";
        }
    }

    // ui
    const box = document.createElement('div');
    box.style.zIndex = 9999;
    box.style.position = 'fixed';
    box.style.bottom = '1rem';
    box.style.left = '1rem';
    box.style.backgroundColor = '#777';
    box.style.padding = '0.5rem';
    box.style.borderRadius = '0.3rem';

    const title = document.createElement('h3');
    title.textContent = "Tsync";
    box.appendChild(title);

    const updateBtn = document.createElement('button');
    updateBtn.textContent = "Update tsync test";
    updateBtn.addEventListener('click', tsync);
    box.appendChild(updateBtn);

    const keyBtn = document.createElement('button');
    keyBtn.textContent = "API Key";
    keyBtn.addEventListener('click', updateApiKey);
    box.appendChild(keyBtn);

    const updateBox = document.createElement('div');
    updateBox.innerHTML = '<span>auto update</span>';
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
