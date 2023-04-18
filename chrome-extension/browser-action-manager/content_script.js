function myAlert(event){
    let text = event.target.innerText;
    console.log(text);
    alert(text)

    const req = new XMLHttpRequest();
    req.open("POST", "http://localhost:8012", true);
    req.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    req.send(JSON.stringify({
        "xpath": getPathTo(event.target),
    }))
}

function getPathTo(element) {
    if (element===document.body)
        return element.tagName;

    var ix= 0;
    var siblings= element.parentNode.childNodes;
    for (var i= 0; i<siblings.length; i++) {
        var sibling= siblings[i];
        if (sibling===element)
            return getPathTo(element.parentNode)+'/'+element.tagName+'['+(ix+1)+']';
        if (sibling.nodeType===1 && sibling.tagName===element.tagName)
            ix++;
    }
}

document.getElementsByTagName('html')[0].addEventListener('click', myAlert);
