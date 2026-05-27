function renderScreenTypeFields(container, typeKey, values = {}) {
    container.innerHTML = "";
    if (!typeKey || !SCREEN_TYPES[typeKey]) {
        return false;
    }

    const spec = SCREEN_TYPES[typeKey];
    for (const field of spec.fields) {
        const label = document.createElement("label");
        label.textContent = field.label;
        label.htmlFor = `field-${field.name}`;

        const input = document.createElement("input");
        input.id = `field-${field.name}`;
        input.name = field.name;
        input.type = field.type || "text";
        if (field.placeholder) {
            input.placeholder = field.placeholder;
        }
        if (field.type !== "password" && values[field.name]) {
            input.value = values[field.name];
        }
        if (field.type === "password") {
            input.placeholder = field.placeholder || "Leave blank to keep current";
            input.required = false;
            input.autocomplete = "off";
        } else if (field.required) {
            input.required = true;
        }

        const wrap = document.createElement("p");
        wrap.appendChild(label);
        wrap.appendChild(document.createTextNode(" "));
        wrap.appendChild(input);
        container.appendChild(wrap);
    }
    return true;
}
