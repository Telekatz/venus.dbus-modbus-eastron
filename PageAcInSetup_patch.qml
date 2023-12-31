/* Eastron settings */
	MbItemOptions {
			description: qsTr("Phase")
			bind: Utils.path(root.bindPrefix, "/Phase")
			show: productId == 0xb023 && valid
			possibleValues: [
				MbOption { description: "L1"; value: 0 },
				MbOption { description: "L2"; value: 1 },
				MbOption { description: "L3"; value: 2 }
			]
		}
/* Eastron settings end */