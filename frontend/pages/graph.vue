<template>
  <div class="row">
    <div class="col-sm-12 col-md-12">
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
      networks: [],
      mask:[],
      routes: [],
      devices: [],
      check:[],
      network_in_link: [],
      links: [],
      checkGraphEdge: []
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
    calculate_usage_percent(src_usage, dst_usage, speed) {
      return Math.max(src_usage, dst_usage) / speed * 100;
    },
    async fetchGraph() {
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
      this.graphRawData = await this.$axios.$get("link");
      this.updateGraph();
    },
    getNetwork() {
      for (var i = 0; i < this.routes.length; i++) {
       for (var j = 0; j < this.routes[i].length; j++) {
         if (this.networks.indexOf(this.routes[i][j].dst) < 0 && this.routes[i][j].dst != "0.0.0.0" && this.routes[i][j].mask != "255.255.255.255") {
            this.networks.push(this.routes[i][j].dst);
            this.mask.push(this.subnetToCidr(this.routes[i][j].mask));
          }
        }
      }
    },
    getNetworkFromIP(ip, mask) {
      //alert(ip+", "+mask);
      var check = "";
      ip = ip.split(".");
      mask = mask.split(".");
      for (var i=0; i < mask.length; i++) {
        if (mask[i] != "255") {
          ip [i] = parseInt(ip[i], 10).toString(2).padStart(8, "0");
          mask[i] = parseInt(mask[i], 10).toString(2).padStart(8, "0");
          for (var j=0; j < mask[i].length; j++){
            if (mask[i][j] == "0") {
              check += "0";
            } else {
              check += ip[i][j];
            }
          }
          ip[i] = parseInt(check, 2);
        }
      }
      return ip.join(".");
    },
    count(list, check) {
      var count = 0;
      for (var i=0; i < list.length; i++) {
        if (list[i] == check) {
          count = count +1;
        }
      }
      return count;
    },
    getNetworkInLink() {
      for (var i=0; i < this.links.length; i++) {
        for (var a=0; a<this.devices.length; a++) {
          if (this.devices[a]._id.$oid == this.links[i].src_node_id.$oid || this.devices[a]._id.$oid == this.links[i].dst_node_id.$oid) {
            for (var b=0; b<this.devices[a].interfaces.length; b++) {
              if (this.links[i].src_ip == this.devices[a].interfaces[b].ipv4_address){
                this.network_in_link.push(this.getNetworkFromIP(this.links[i].src_ip, this.devices[a].interfaces[b].subnet));
              }
            }
          }
        }
      }
    },
    findInterfaces(src_node_id, dst_node_id, ip) {
      for (var a=0; a<this.devices.length; a++) {
        if (this.devices[a]._id.$oid == src_node_id.$oid || this.devices[a]._id.$oid == dst_node_id.$oid) {
          for (var b=0; b<this.devices[a].interfaces.length; b++) {
            if (ip == this.devices[a].interfaces[b].ipv4_address){
              return this.devices[a].interfaces[b];
            }
          }
        }
      }
    },
    updateGraph() {
      this.network_in_link = [];
      this.getNetworkInLink();
      if (this.graphRawData.links) {
        this.graphEdge = [];
        this.graphNode = [];
        this.check = [];
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
          var ifaces = this.findInterfaces(link.src_node_id, link.dst_node_id, link.src_ip);
          const edge = {
            from: link.src_node_ip,
            to: link.dst_node_ip,
            width: link.link_min_speed / 400000,
            // value: link.src_in_use + link.dst_in_use,
            label: this.getNetworkFromIP(link.src_ip, ifaces.subnet)+"/"+ this.subnetToCidr(ifaces.subnet) +"("+ `${speed.toFixed(2)}%` + ")",
            id: edgeId,
            color: { color, highlight: color }
          };
          if (link.link_min_speed > 1544000) {
            edge.width = 1544000 /400000;
          }
          if (link.src_ip != link.dst_ip){
            this.check.push(this.getNetworkFromIP(link.src_ip, ifaces.subnet));
            //alert(link.src_ip +", "+ link.dst_ip);
            if (this.count(this.network_in_link, this.getNetworkFromIP(link.src_ip, ifaces.subnet)) <= 1 && ifaces.admin_status == 1 && ifaces.operational_status == 1) {
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
        for (var i=0; i < this.networks.length; i++){
          if ((!nodes_[this.networks[i]] && this.check.indexOf(this.networks[i]) < 0)||(this.count(this.network_in_link, this.networks[i]) > 2)){
            let label = this.networks[i]+"/"+this.mask[i];
            nodes_[this.networks[i]] = {
              id: this.networks[i],
              value: 1,
              label: label,
              color: "#FFF"
            };
            id++;
            for (var j=0; j < this.devices.length; j++) {
              for (var k=0; k < this.devices[j].interfaces.length; k++) {
                if (this.devices[j].interfaces[k].ipv4_address) {
                  if(this.getNetworkFromIP(this.devices[j].interfaces[k].ipv4_address, this.devices[j].interfaces[k].subnet) == this.networks[i]) {
                    let color = "rgb(144, 238, 144)";
                    const edge = {
                      from: this.devices[j].interfaces[k].device_ip,
                      to: this.networks[i],
                      id: this.devices[j].interfaces[k].device_ip+this.networks[i],
                      color: { color, highlight: color },
                      width: 1544000 / 400000
                    }
                    if (this.graphEdge.map(function(e) { return e.id; }).indexOf(edge.id) < 0) {
                      this.graphEdge.push(edge);
                      this.graph.addEdge(this.devices[j].interfaces[k].device_ip, this.networks[i]);
                    }
                  }
                }
              }
            }
          }
        };
        this.nodes_ = nodes_;
        this.graphNode = Object.values(nodes_);
        if (this.checkGraphEdge.length == 0) {
          this.checkGraphEdge = this.graphEdge;
        }
        else if (this.checkGraphEdge.length != this.graphEdge.length) {
          location.reload();
        }
        else {
          for (var i=0;i<this.graphEdge.length;i++) {
            if (this.graphEdge[i].from != this.checkGraphEdge[i].from || this.graphEdge[i].to != this.checkGraphEdge[i].to) {
              location .reload();
            }
          }
        }
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
