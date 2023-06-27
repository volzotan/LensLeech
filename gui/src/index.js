import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import Stats from 'stats.js';
import KalmanFilter from 'kalmanjs';

const   PATTERN_FILE  = "2678_data_3_i-1725881.json",
        WS_URI        = "ws://192.168.178.20:5006",
        WS_URI2       = "ws://localhost:5006",
        BLOB_FILE     = "blob.obj",
        ARROW_FILE    = "arrow.obj",
        ARROW_C_FILE  = "arrow_circular.obj",
        HEX_SIZE      = 1.0,
        POINT_SIZE    = 0.5;

const   SPHERE_RADIUS = 60/2,
        SPHERE_DIST   = 25.055; // measured from work position zero

const   kf = new KalmanFilter();
var     rotation = null;

var     status = 0; // -1 error | 0 default | 1 connected | 2 blob present
var     mode = null;

var stats = new Stats();
// stats.showPanel(0); // 0: fps, 1: ms, 2: mb, 3+: custom
// document.body.appendChild(stats.dom);

// from: https://stackoverflow.com/a/10627148/2669317
document.getElementById("btn-fullscreen").addEventListener("click", function() {
    if ((document.fullScreenElement && document.fullScreenElement !== null) || (!document.mozFullScreen && !document.webkitIsFullScreen)) {
        if (document.documentElement.requestFullScreen) {  
            document.documentElement.requestFullScreen();  
        } else if (document.documentElement.mozRequestFullScreen) {  
            document.documentElement.mozRequestFullScreen();  
        } else if (document.documentElement.webkitRequestFullScreen) {  
            document.documentElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);  
        }  
    } else {  
        if (document.cancelFullScreen) {  
            document.cancelFullScreen();  
        } else if (document.mozCancelFullScreen) {  
            document.mozCancelFullScreen();  
        } else if (document.webkitCancelFullScreen) {  
            document.webkitCancelFullScreen();  
        }  
    }  
}, false);

const canvas = document.querySelector("#c");
const renderer = new THREE.WebGLRenderer({canvas, alpha: true});

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
// const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 1000);

camera.position.set(0, 150, 70);
// camera.position.set(70, 150, 70);
// camera.position.set(0, 200, 0);
camera.lookAt(0, 0, 0);

// scene.background = new THREE.Color(0x4D4D4D);
scene.background = new THREE.Color(0x333333);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 0, 0);
controls.update();

const intensity = 1;
const light = new THREE.HemisphereLight(0xffffff, 0x080820, intensity);
scene.add(light);

const material_base = new THREE.MeshPhongMaterial({
    color: 0x202020, 
    transparent: true,
    opacity: 0.2,  
    flatShading: true
});

const material_blue = new THREE.MeshPhongMaterial({
    color: 0x0000FF, 
    transparent: true,
    opacity: 0.2,  
    flatShading: true
});

const material_green = material_blue.clone();
material_green.color = new THREE.Color(0x00FF00);
const material_blue_bright = new THREE.MeshPhongMaterial({color: 0x0000FF});
const material_green_bright = new THREE.MeshPhongMaterial({color: 0x00FF00});

const material_blob = new THREE.MeshPhongMaterial({
    color: 0xCCCCCC,  
    transparent: true,
    opacity: 0.9,  
    flatShading: true,
});

const material_arrow_default = new THREE.MeshPhongMaterial({
    color: 0xFF0000,  
    transparent: true,
    opacity: 0,  
    flatShading: true,
});
const material_arrow_squeeze = material_arrow_default.clone();
const material_arrow_press = material_arrow_default.clone();
const material_arrow_push = material_arrow_default.clone();

const material_degticks = new THREE.MeshPhongMaterial({
    color: 0xAAAAAA,
    transparent: true,
    opacity: 0,  
    flatShading: true,
});

const material_capsule = new THREE.MeshPhongMaterial({
    color: 0x00FF00,
    transparent: true,
    opacity: 0,  
    flatShading: true,
});

const base = new THREE.Mesh(new THREE.CylinderGeometry(25, 25, 1, 64), material_base);
scene.add(base);

const group_blob = new THREE.Group();
const group_push_arrows = new THREE.Group();

var pattern = {};
var pattern_pos = {};
const loader = new OBJLoader();

// blob

loader.load(BLOB_FILE, function (obj) {

    obj.rotation.x = THREE.MathUtils.degToRad(-90);

    const mesh = obj.children[0];
    mesh.material = material_blob;

    fetch(PATTERN_FILE)
        .then((response) => response.json())
        .then((json) => {

            for (const [key, value] of Object.entries(json["data"])) {

                const   pos = pointy_hex_to_pixel(key.split("|"), HEX_SIZE),
                        dome_offset = calculate_dome_offset(pos[0], pos[1], SPHERE_DIST, SPHERE_RADIUS);
                var mat = [null, null];

                switch(value) {
                    case 0:
                        mat = [material_blue, material_blue_bright];
                        break;
                    case 1:
                        mat = [material_green, material_green_bright];
                        break;
                    default:
                        console.log("unknown pattern value!")
                } 

                const dot = new THREE.Mesh(new THREE.DodecahedronGeometry(POINT_SIZE, 1), mat[0]);
                dot.position.set(pos[0], SPHERE_DIST + dome_offset - POINT_SIZE, pos[1]);
                group_blob.add(dot);
                pattern[key] = [dot, mat[0], mat[1]];
                pattern_pos[key] = SPHERE_DIST + dome_offset - POINT_SIZE;
            }
        });


    group_blob.add(obj);

}, undefined, function (error) {
    console.log(error);
});

loader.load(ARROW_FILE, function (obj) {

    // squeeze arrows

    const mesh = obj.children[0];
    mesh.material = material_arrow_squeeze;

    const arrow_right = obj.clone();
    arrow_right.position.set(25, 17, 0);
    arrow_right.rotation.z = THREE.MathUtils.degToRad(90);   
    arrow_right.rotation.x = THREE.MathUtils.degToRad(90);
    group_blob.add(arrow_right);

    const arrow_left = obj.clone();
    arrow_left.position.set(-25, 17, 0);
    arrow_left.rotation.z = THREE.MathUtils.degToRad(-90);   
    arrow_left.rotation.x = THREE.MathUtils.degToRad(90);
    group_blob.add(arrow_left);

    // const num_ticks = 8;
    // for (let i = 0; i < num_ticks; i++) { 
    //     const arrow_dpad = obj.clone();
    //     arrow_dpad.children[0].material = material_arrow_push;
    //     const rad = THREE.MathUtils.degToRad((360/num_ticks)*i);
    //     arrow_dpad.position.set(56 * Math.sin(rad), 1, 56 * Math.cos(rad));
    //     arrow_dpad.rotation.x = THREE.MathUtils.degToRad(90);
    //     arrow_dpad.rotation.z = -rad;
    //     group_blob.add(arrow_dpad);
    // }

    // press arrow

    mesh.material = material_arrow_press;

    const arrow_press = obj.clone();
    arrow_press.position.set(0, 40, 1);
    arrow_press.rotation.x = THREE.MathUtils.degToRad(180);   
    group_blob.add(arrow_press);

    // push arrow

    mesh.material = material_arrow_push;
    const dist = 30;
    
    const arrow_push = obj.clone();
    arrow_push.position.set(0, 5, -dist);
    arrow_push.rotation.z = THREE.MathUtils.degToRad(-180);   
    arrow_push.rotation.x = THREE.MathUtils.degToRad(90);
    group_push_arrows.add(arrow_push);

    scene.add(group_push_arrows);

}, undefined, function (error) {
    console.log(error);
});


// ticks

const capsule = new THREE.Mesh(new THREE.CapsuleGeometry(1.0, 8, 4, 8), material_capsule);
capsule.rotation.x = THREE.MathUtils.degToRad(90);
capsule.position.set(0, 0, -50);

const num_ticks = 128;
for (let i = 0; i < num_ticks; i++) { 
    var tick = null;

    if (i % Math.floor(num_ticks/8) == 0) {
        tick = new THREE.Mesh(new THREE.CapsuleGeometry(0.25, 10, 4, 8), material_degticks);
    } else {
        tick = new THREE.Mesh(new THREE.CapsuleGeometry(0.25, 5, 4, 8), material_degticks); 
    }

    const rad = THREE.MathUtils.degToRad((360/num_ticks)*i);

    tick.rotation.x = THREE.MathUtils.degToRad(90);
    tick.rotation.z = -rad;
    tick.position.set(50 * Math.sin(rad), 0, 50 * Math.cos(rad));
    scene.add(tick);
}

group_blob.add(capsule);
scene.add(group_blob);

function calculate_dome_offset(x, y, distance, radius) {
    const xy_dist = Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2));
    return Math.sqrt(Math.pow(radius, 2) - Math.pow(xy_dist, 2)) - distance;
}

function pointy_hex_to_pixel(qrs, size) {
    var x = size * (Math.sqrt(3) * qrs[0] +  Math.sqrt(3)/2 * qrs[1])
    var y = size * (                                   3./2 * qrs[1])
    return [x, y]
}

function animate() {

    stats.begin();
    renderer.render(scene, camera);
    stats.end();

    requestAnimationFrame(animate);
};

function update(info) {

    // group_blob.rotation.y = info["rotation"];
    if (info["rotation"] != null) {
        group_blob.rotation.y = kf.filter(info["rotation"]);
    }

    // update_mode(info["mode"]);
    update_mode("all");

    if (info["found_patterns"].length > 3) {
        update_status(2);
    } else {
        // update_status(1);
    }

    for (const qrs of Object.keys(pattern)) {
        if (info["found_patterns"].includes(qrs)) {
            pattern[qrs][0].material = pattern[qrs][2]
        } else {
            pattern[qrs][0].material = pattern[qrs][1]
        }
    }

    if (info["squeeze"]) {
        material_arrow_squeeze.opacity = 1.0;
    } else {
        material_arrow_squeeze.opacity = 0;
    }

    if (info["press"]) {
        material_arrow_press.opacity = 1.0;
    } else {
        material_arrow_press.opacity = 0;
    }
    
    if (info["press_values"]) {
        for (const [qrs, val] of Object.entries(info["press_values"])) {
            var posY = pattern_pos[qrs];
            posY += val * -10; 
            pattern[qrs][0].position.setY(posY);
        }
    }

    if (info["push"]) {
        const d = info["push"];
        const thres = 0.25;

        if (Math.abs(d[0]) + Math.abs(d[1]) > thres) {

            // group_push_arrows.rotation.y = (Math.atan2(d[1], d[0]) + Math.PI/2) % Math.PI*2;
            const num_buckets = 8,
                size_bucket = Math.PI*2/num_buckets;
            group_push_arrows.rotation.y = Math.floor((Math.atan2(d[1], d[0]) - Math.PI/2)/size_bucket)*size_bucket;
            material_arrow_push.opacity = 1.0;

        } else {
            material_arrow_push.opacity = 0;
        }
    }
}

function update_mode(new_mode) {
    if (mode != new_mode) {
        mode = new_mode;

        var infobox = document.getElementById("info_mode");

        console.log("mode: " + mode);

        switch (mode) {
            case "all":
                material_degticks.opacity = 1.0;
                material_capsule.opacity = 1.0;
                infobox.innerHTML = "";
                break; 
            case "rotation":
                material_degticks.opacity = 1.0;
                material_capsule.opacity = 1.0;
                infobox.innerHTML = "MODE: rotation";
                break;
            case "press":
                infobox.innerHTML = "MODE: press";
                break;
            case "push":
                infobox.innerHTML = "MODE: push";
                break;
            default:
                material_degticks.opacity = 0;
                material_capsule.opacity = 0;
                infobox.innerHTML = "";
        }
    }
}

function update_status(new_status) {
    
    if (status != new_status) {
        status = new_status;

        var infobox = document.getElementById("info_connection");

        switch (status) {
            case 0:
                material_blob.opacity = 0.0;
                infobox.innerHTML = "STATUS: disconnected";
                break;
            case 1:
                material_blob.opacity = 0.1;
                infobox.innerHTML = "STATUS: no blob detected";
                break;
            case 2:
                scene.background = new THREE.Color(0xFFFFFF);
                material_blob.opacity = 0.8;
                infobox.innerHTML = "STATUS: blob present";
                break;
            default:
                scene.background = new THREE.Color(0xFF0000);
                infobox.innerHTML = "STATUS: error";
        }
    }  
}

var ws = new WebSocket(WS_URI);
ws.onopen = function() {
    console.log('ws connected');
    update_status(1);
};
ws.onclose = function() {
    console.log('ws closed');
    update_status(0);
};
ws.onerror = function() {
    console.log('ws error');

    ws = new WebSocket(WS_URI2);
    ws.onerror = function() {
        console.log('ws error backup URI');
        update_status(-1);
    };
};
ws.onmessage = function(msgevent) {
    var msg = JSON.parse(msgevent.data);
    update(msg);
};

function onResize() {
    const canvas = document.querySelector('#c');
    const pixelRatio = window.devicePixelRatio;
    const width  = canvas.clientWidth  * pixelRatio | 0;
    const height = canvas.clientHeight * pixelRatio | 0;

    camera.aspect = canvas.clientWidth / canvas.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
}

window.addEventListener('resize', onResize, false);

onResize();
requestAnimationFrame(animate);