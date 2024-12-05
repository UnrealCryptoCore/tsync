function dropHandler(ev) {
    ev.preventDefault();
    const fileinp = document.getElementById('fileinp')
    fileinp.files = ev.dataTransfer.files;
    // Use DataTransfer interface to access the file(s)
    [...ev.dataTransfer.files].forEach((file, i) => {
        console.log(file);
        console.log(`… file[${i}].name = ${file.name}`);
    });
}

function dragOverHandler(ev) {
    console.log("File(s) in drop zone");

    // Prevent default behavior (Prevent file from being opened)
    ev.preventDefault();
}
