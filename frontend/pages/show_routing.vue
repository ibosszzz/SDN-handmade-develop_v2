<template>
  <div class="row">
    <div class="col-sm-12 col-md-12">
      <form class="card" @submit.prevent="onSubmit" method="post">
        <div class="card-header">
          <h3 class="card-title">Route</h3>
        </div>
		<div class="card-body">
		  <div class="row">
            <div class="col-md-4">
              <div class="form-group">
                <label class="form-label">Source</label>
                <select @change="onActionChange(i)" v-model="source" class="form-control">
                  <option value="0" disabled>Select source</option>
                  <option v-for="network in networks" :key="network" :value="network">{{network}}/{{ mask[networks.indexOf(network)] }}</option>
                </select>
              </div>
            </div>
	    <div class="col-md-4">
              <div class="form-group">
                <label class="form-label">Destination</label>
                <select @change="onActionChange(i)" v-model="destination" class="form-control">
                  <option value="0" disabled>Select destination</option>
                  <option v-for="network in networks" :key="network" :value="network">{{ network }}/{{ mask[networks.indexOf(network)] }}</option>
                </select>
              </div>
            </div>
            <div class="col-md-4">
              <button style="margin-top:25px" type="submit" class="btn btn-primary">Ok</button>
            </div>
          </div>
	    </div>
      </form>
      <div class="card">
        <div class="card-header">
          Network graph
        </div>
        <div class="card-body">
          <network-graph :nodes="graphNode" :edges="graphEdge" @click="onClick" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import NetworkGraph from "@/components/NetworkGraph.vue";
import * as jsnx from "jsnetworkx";
import ipaddrMixin from "@/mixins/ipaddr";

export default {
  data() {
    return {
      devices: [],
      mode: "findpath",
      graph: null,
      node_label: "hostname",
      graphRawData: null,
      nodes_: {},
      graphNode: [],
      graphEdge: [],
      interval: null,
      eventName: "",
      information: "",
      selectEdge: ["192.168.2.0-192.168.2.1", "192.168.2.2-192.168.2.3"],
      nodeSelect: [],
      highlightNode: [],
      routes: [],
      source: "",
      destination: "",
      networks: [],
      mask:[],
      links: [],
      deviceID: "",
      addlink: [],
    };
  },
  components: {
    NetworkGraph
  },
  mixins: [ipaddrMixin],
  async mounted(){
    await this.fetchData();
  },
  methods: {
    async onSubmit(n) {
      let check = true;
      this.deviceID = this.getDeviceIDFromNetwork(this.source);
      while (check) {
      	check = this.getNextHopIP();
      }
    },
    async onClick(param) {
      this.eventName = "onClick"
      this.information = param
      if (this.mode == "findpath") {
        if (this.nodeSelect.length >= 2) {
          this.nodeSelect = [];
        }
        this.highlightNode = [];
        if (param.nodes.length < 1) {
          this.updateGraph();
          return;
        }
        this.nodeSelect.push(param.nodes[0]);
        // this.highlightNode = [];
        if (this.nodeSelect.length == 2) {
          const rawData = await this.$axios.$get(
            `path/${this.nodeSelect[0]},${this.nodeSelect[1]}`
          );
          this.highlightNode = rawData.paths;
        }
        this.updateGraph();
        // await this.$axios.$get("path/" + ip);
        return;
      }
      const info = param;
      if (param.nodes) {
        const ip = param.nodes[0];
        const device = await this.$axios.$get("device/ifip/" + ip);
        info["device"] = device;
      }
      this.eventName = "onClick";
      this.information = JSON.stringify(info, null, 2);
    },
    getNetwork() {
      for (var i = 0; i < this.routes.length; i++) {
	for (var j = 0; j < this.routes[i].length; j++) {
	  if (this.networks.indexOf(this.routes[i][j].dst) < 0 && this.routes[i][j].dst != "0.0.0.0" && this.routes[i][j].mask != "255.255.255.255") {
            this.networks.push(this.routes[i][j].dst);
            this.mask.push(this.subnetToCide(this.routes[i][j].mask));
      	  }
	}
      }
    },
    getDeviceIDFromNetwork(network) {
      for (var i=0; i < this.routes.length; i++) {
	for (var j=0; j < this.routes[i].length; j++) {
          if (this.routes[i][j].dst == network && this.routes[i][j].proto == 2) {
            return this.routes[i][j].device_id.$oid;
          }
	}
      }
    },
    getNextHopIP () {
      for (var i=0; i < this.routes.length; i++) {
      	if (this.routes[i][0].device_id.$oid == this.deviceID) {
	  for (var j=0; j < this.routes[i].length; j++) {
	    if (this.routes[i][j].dst == this.destination) {
	      if (this.routes[i][j].next_hop == "0.0.0.0") {
	        return false;
	      } else {
			this.deviceID = this.getLink(this.routes[i][j].next_hop);
			return true;
	      }
	    }
	  }
      	}
      }
    },
    getLink (next_hop) {
      for (var i=0; i < this.links.length; i++) {
      	if (this.deviceID == this.links[i].src_node_id.$oid && next_hop == this.links[i].dst_ip) {
      	  this.addlink.push([this.links[i].src_ip, this.links[i].dst_ip]);
      	  return this.links[i].dst_node_id.$oid;
      	} else if (this.deviceID == this.links[i].dst_node_id.$oid && next_hop == this.links[i].src_ip) {
      	  this.addlink.push(this.links[i].src_ip, this.links[i].dst_ip);
      	  return this.links[i].src_node_id.$oid;
      	}
      }
    },
    calculate_usage_percent(src_usage, dst_usage, speed) {
      return Math.max(src_usage, dst_usage) / speed * 100;
    },
    async fetchGraph() {
      this.graphRawData = await this.$axios.$get("link");
      this.updateGraph();
    },
    updateGraph() {
      if (this.graphRawData.links) {
        this.graphEdge = [];
        this.graphNode = [];
        let nodes_ = {};
        let id = 1;
        // Max - Min in API
        this.graphRawData.links.forEach((link, i) => {
          // Calculate link usage
          const speed = this.calculate_usage_percent(
            Math.max(link.src_in_use, link.src_out_use),
            Math.max(link.dst_in_use, link.dst_out_use),
            link.link_min_speed
          );
          let color;
          if (speed < 50) {
            color = "rgb(144, 238, 144)";
          } else if (speed < 85) {
            color = "rgb(255, 165, 0)";
          } else {
            color = "rgb(255, 0, 0)";
          }
          const edgeId = `${link.src_if_ip}-${link.dst_if_ip}`;
          // Todo Fix highlight edges
          this.highlightNode.forEach(node => {
            if (
              node.indexOf(link.src_node_ip) > -1 ||
              node.indexOf(link.dst_node_ip) > -1
            ) {
              color = "rgb(0, 0, 153)";
            }
          });

          const edge = {
            from: link.src_node_ip,
            to: link.dst_node_ip,
            width: link.link_min_speed / 400000,
            // value: link.src_in_use + link.dst_in_use,
            label: `${speed.toFixed(2)}%`,
            id: edgeId,
            color: { color, highlight: color }
          };
          for (var i=0; i < this.addlink.length; i++) {
          	if (link.src_ip != link.dst_ip && this.addlink.indexOf(link.src_ip) >= 0 && this.addlink.indexOf(link.dst_ip) >= 0) {
    	      this.graphEdge.push(edge);
              this.graph.addEdge(link.src_node_ip, link.dst_node_ip);
      	    }
          }
          if (!nodes_[link.src_node_ip]) {
            let label;
            switch (this.node_label) {
              case "hostname":
                label = link.src_node_hostname;
                break;
            }
            nodes_[link.src_node_ip] = {
              id: link.src_node_ip,
              value: 1,
              label: label
            };
            id++;
          }
          if (!nodes_[link.dst_node_ip]) {
            let label;
            switch (this.node_label) {
              case "hostname":
                label = link.dst_node_hostname;
                break;
            }
            nodes_[link.dst_node_ip] = {
              id: link.dst_node_ip,
              value: 1,
              label: label
            };
            id++;
          }
        });
        this.nodes_ = nodes_;
        this.graphNode = Object.values(nodes_);
      }
    }
  },
  
  async mounted() {
    // console.log(jsnx)
    this.graph = new jsnx.Graph();
    this.interval = setInterval(() => this.fetchGraph(), 1000);
    try {
      let res = await this.$axios.$get("device");
      this.devices = res.devices;
      res = await this.$axios.$get("link");
      this.links = res.links;
      let res2;
      let device;
      for (var i = 0; i < this.devices.length; i++) {
        device = this.devices[i];
        res2 = await this.$axios.$get(`routes/${device._id.$oid}`);
        if (res2) {
          this.routes.push(res2.routes);
        }
      }
      this.getNetwork();
    } catch (e) {}
    this.form = {
      ...this.propForm
    };
  },
  beforeDestroy() {
    clearInterval(this.interval);
  }
};
</script>

