from twisted.python import log
from twisted.internet import reactor
from twisted.application import service
from twisted.internet.protocol import DatagramProtocol, Protocol, Factory

from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory


SERVER_IP = "127.0.0.1"
SERVER_UDP_PORT = 5005
SERVER_WS_PORT = 5006
SERVER_HTTP_PORT = 8000
SERVER_HTTP_RESOURCES = "."


class Bridge():

  def __init__(self):
    self.udpServer = None
    self.wsServer = None

  def setUdpServer(self, udpServer):
    self.udpServer = udpServer

  def setWebsocketServer(self, wsServer):
    self.wsServer = wsServer

  def udpToWebsocket(self, data):
    if self.wsServer is not None:
      self.wsServer.sendMessage(data, False)

  def websocketToUdp(self, data):
    if self.udpServer is not None:
      self.udpServer.transport.write(data, (CLIENT_IP, CLIENT_UDP_PORT))

# udp server

class UDPServer(DatagramProtocol):

  def __init__(self, bridge):
    self.bridge = bridge
    self.bridge.setUdpServer(self)

  def datagramReceived(self, data, host):
    # print(data)
    self.bridge.udpToWebsocket(data)

# websocket server

class BridgedWebSocketServerFactory(WebSocketServerFactory):

  def __init__(self, url, bridge):
    WebSocketServerFactory.__init__(self, url)
    self.bridge = bridge

class WebSocketServer(WebSocketServerProtocol):

  def onOpen(self):
    print('WebSocket connection open.')

  def onConnect(self, request):
    self.factory.bridge.setWebsocketServer(self)
    print('Client connecting: {0}'.format(request.peer))

  # def onMessage(self, payload, isBinary):
  #   self.factory.bridge.websocketToUdp(payload)

  def onClose(self, wasClean, code, reason):
    print('WebSocket connection closed: {0}'.format(reason))

# initalize servers

if __name__ == '__main__':

  bridge = Bridge()

  # log.startLogging(sys.stdout)

  # websocket setup

  wsAddress = "ws://{}:{}".format(SERVER_IP, SERVER_WS_PORT)

  factory = BridgedWebSocketServerFactory(wsAddress, bridge)
  factory.protocol = WebSocketServer
  reactor.listenTCP(SERVER_WS_PORT, factory)

  # http setup

  site = Site(File("."))
  reactor.listenTCP(SERVER_HTTP_PORT, site)

  # udp setup

  reactor.listenUDP(SERVER_UDP_PORT, UDPServer(bridge))

  # start session

  print("server running...")
  reactor.run()

