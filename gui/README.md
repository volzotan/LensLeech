![Screenshot](/media/gui.png)

The LensLeech visualization is a three.js script that receives status updates as JSON dictionaries via a websocket connection. The image processing pipeline wraps all detection results in a UDP package each frame. 
This works because a python server based on twisted/autobahn maintains the websocket connection while forwarding the payload of received UDP packages to the websocket connection. The python server serves the static files (HTML, JS, 3d models) as well.

Install npm packages:
```
npm install
```

Install python packages:
```
pip3 install -r requirements.txt
```

Run webpack to package the JS files:
```
webpack
```

Start the HTTP server and UDP to websocket bridge:
```
python3 serve.py
```

Open the website:
```
localhost:8000
```
