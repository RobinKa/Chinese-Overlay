import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11
import QtQuick.Dialogs 1.1
import QtQuick.Shapes 1.11
import QtQuick.Window 2.2

Rectangle {
    id: mainWindow
    //anchors.fill: parent
    width: 640
    height: 480
    color: "transparent"

    Component {
        id: overlayTemplate
        Rectangle {
            id: rect
            property var overlayInfo

            width: overlayText.contentWidth
            height: overlayText.contentHeight

            opacity: 0.8
            color: "#0095ff"

            x: overlayInfo.position[0]
            y: overlayInfo.position[1]

            Text {
                id: overlayText
                text: overlayInfo.text
                font.pixelSize: 12
                font.weight: Font.Light
            }

            ToolTip {
                id: toolTip
                text: overlayInfo.tooltip
                visible: mouseArea.containsMouse
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
            }
        }
    }

    Component.onCompleted: {
        const activeWindows = []
        const pooledWindows = []

        function onOverlayInfoAdded(overlayInfo) {
            let window = null

            if (pooledWindows.length > 0) {
                window = pooledWindows.pop()
                window.overlayInfo = overlayInfo
                window.visible = true
            } else {
                window = overlayTemplate.createObject(mainWindow, {
                    "overlayInfo": overlayInfo
                })
            }

            activeWindows.push(window)
        }

        function onOverlayInfoCleared() {
            for (let i = 0; i < activeWindows.length; i++) {
                activeWindows[i].visible = false
                pooledWindows.push(activeWindows[i])
            }
            activeWindows.length = 0
        }

        backend.onOverlayInfoAdded.connect(onOverlayInfoAdded)
        backend.onOverlayInfoCleared.connect(onOverlayInfoCleared)
    }
}