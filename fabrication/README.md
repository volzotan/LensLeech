
# Choice of silicone

Most elastomer sensor papers report using either [XP-565](http://www.silicones-inc.com/index.php/about/product-datasheets/addition-cure-silicone-products-data-sheets/) from Silicones, Inc. or [Solaris](https://www.smooth-on.com/product-line/solaris/) by Smooth-On, a clear encapsulating rubber sold for potting solar cells or electronics. Both silicones are platinum-based RTV (room-temperature-vulcanizing) silicones and have a hardness of about Shore A15. However, XP-565 was impossible to purchase in Europe at the time of writing and Solaris is expensive at 133 EUR per kilogram.

![tinted silicone|500](/media/white-silicone.jpg)

When evaluating other silicones purchase with care. Silicones labeled as "translucent" usually are not optically clear but have a strong milky, white-ish tint. Silicones labeled as transparent may be optically clear or have a similar white tint. Another issue is that some optically-clear silicones are sold as special effects/FX/glass/ice material. Examples "Silglas25", Smooth-On's "Rubber Glass", etc. These break very easily (thus work really well for imitating crushed ice but not very well for durable and flexible silicone parts). While these silicones may make sense for some tests and prototyping, keep in mind that unmolding the cured silicone part is considerably harder with a part that ruptures easily and users may break the part in a user study.

What worked well, in the end, is [Trollfactory's Type 19](https://trollfactory.de/produkte/silikon-kautschuk/haertegrad-shore/weich-shore-a25/7056/tfc-silikon-kautschuk-typ-19-glasklar-transparent-shore-1-1-special-effect). Type 19 has a Shore hardness of A19, is sold in small quantities suitable both for testing as well as rapid prototyping and is (almost perfectly) optically clear. In thick sections, a slight whiteish tint can be observed, but this is not an issue for image-processing tasks. The major issue of Type 19 is a very high viscosity and short pot life of about 5 minutes. Degassing and pouring with a mold that has a complex geometry or a narrow sprue is challenging. 

Tip: Cooling the silicone before mixing does slow down the curing reaction. Adding solvent can lower the viscosity, but too much solvent will result in shrinking and way too much solvent may be an issue for the mold material.

# Geometry

![silicone body cross-section|500](/media/blob_crosssection.png)

The steps around the lens are a manufacturing artifact since the mold is milled with a square endmill on a CNC machine. The lens needs about a 45-degree angle of clearance on each side, but some kind of steps or chamfer is required to provide enough rigidity for the foot when squeezed and pressed during an interaction.

We have chosen a lens radius of 7.5mm. The total body height of the silicone body 24.5mm (+1mm for the foot, the lens center must not touch the surface below). The points are arranged in a hexagonal grid, with a distance of 1.5mm horizontally and 1.7mm diagonally at a point size of 1.0mm. This results in a good compromise between physical size, detection robustness, and the number of visible points.

Note: the manufacturer did not specify a refractive index for Type 19 silicone. We assume a refractive index similar to other platinum-cure silicones, Smooth-On Solaris for example has 1.41. Since the silicone blob is a convex-plano lens where the "plano" part of the lens is quite a distance away, "infinite" center thickness is assumed. Using the lensmaker's equation the back focal length would be 0 at a center thickness of ```25.79```. This can be verified by solving the lensmaker's equation for the distance between the lenses or using a focal point calculator (example [Edmund Optics calculator](https://www.edmundoptics.com/knowledge-center/tech-tools/focal-length/), set center thickness = 25.79mm, R1=7.5mm, R2=plano).

The lens surface is clear to refract light with minimal loss. The touch surface is diffuse to improve the detection reliability of the points when the finger touches the surface.

When the finger is hovering above the surface or touching it, strong contrasts tend to create issues for auto white-balance and auto exposure algorithms of various tested cameras.

![clear vs. diffuse|500](/media/comparison_frosted_unfrosted.png)

# Mold

Laser-cut or CNC-machined acrylic glass (PMMA) works well as baseplates for surfaces that need to be flat and smooth. This is especially true for faces of the object that should let light pass unobstructed. The geometry of the silicone body requires that the bottom and top parts of the mold need to be machined on a lathe or a mill. In this case a mill was used.

![mold|500](/media/mold.png)

![mold|500](/media/mold1.jpg)

![mold|500](/media/mold2.jpg)

![mold|500](/media/mold3.jpg)

The optical surfaces are best cut with a ball end mill (the larger the better). What worked best for me using Fusion 360's CAM:

* buy a piece of face-milled aluminium or precision acrylic glass (cast acrylic) of the right height (so no further face-milling is necessary) 
* cut the optical surface using a standard flat endmill and the 3D adaptive toolpath strategy and leave about 0.3mm of material
* follow that up with a 3D spiral toolpath with the ball endmill and leave 0.1mm of material (stepover of 0.3mm is sufficient)
* add a bit of lubricant, for example WD40 or liquid silicone grease or whatever is available
* do the finish pass as a 3D spiral toolpath with a 0.1mm stepover

Important: when using the 3D spiral toolpath Fusion 360 calculates a path that tries to cut as much as possible with the tip of the ball (which spins right in the center of rotation). If the cutting surface of the tool is not actually the lowest end of the tip but one of the outer regions of the cutter, the finish improves further. 

The rest of the mold is 3d-printed on a commodity FDM printer (Prusa i3 Mk3 with standard 0.4mm nozzle) with PETG filament (Colorfabb Economy PETG white) at 0.15mm layer height. SLA printing does offer a smoother surfaces structure but requires fully cured prints since any trace of uncured UV resin will inhibit the vulcanization reaction of the silicone components (refer to [this Smooth-On article](https://www.smooth-on.com/support/faq/210/) for more info, [some](https://blog.honzamrazek.cz/2022/07/preventing-platinum-cure-silicone-cure-inhibition-in-resin-printed-molds/) claim that additional washing and coating with PMMA is required.). 

![CNC with grinding attachment|500](/media/machine5.jpg)

If the CNC machine is not able to mill a precise spherical surface with an optical finish, further grinding or polishing is necessary. I did achieve this by purchasing precision steel balls for ball bearings (7.5mm radius for the small lens, 30mm for the top curvature) and using them as a spherical tool. Grinding and polishing were achieved with diamond lapping paste, spread on the steel ball which was rotated on the acrylic mold part. To move the center of rotation across the curvature to polished, the spinning ball needs to be moved. This was done by placing the steel ball on a rotating table in the CNC machine and writing a script to generate gcode with the necessary movement pattern (the script can be found in ```/fabrication/polish/write.py```).

![polishing script|500](/media/polishing-script.png)

As a polishing compound lapping paste was the simplest solution. Start at 40 microns and lower iteratively down to 2 microns for the final polishing step. 
While 2 microns would usually not constitute an "optical finish", the silicone fails to reproduce details at a certain size. Scratches visible in the mold after polishing at 2 microns were not visible in the silicone body molded off the surface so further improving the surface quality may not be necessary.

# Adding markers

Initially, I tried adding markers by placing a stencil (laser-cut 300g/m<sup>2</sup> paper) on uncured silicone in the mold and then spray-painting the stencil with acrylic paint in a paint can. That's what Yuan et al. proposed in a [master's thesis](http://people.csail.mit.edu/yuan_wz/GelSight1/Wenzhen_Thesis_final.pdf) and their [paper](https://ieeexplore.ieee.org/document/7139016). This did not work out at all for me, the acrylic paint did clog up the laser-cut holes of the stencil and the stencil itself did stick to the uncured silicone, disturbing it as soon as it was removed. When applying acrylic paint on cured silicone it did not bond at all (no additional chemicals such as primer have been used) and could be easily rubbed off. This may have not worked due to the choice of stencil (Yuan reported to have used a PCB which is clever because that's the easiest way to get a CNC-machined part with micro-drilled holes and the fiberglass surface is probably less of an issue compared to absorption-prone paper).

Yuan and others reported success with inkjet printing on transfer paper and applying the transfer paper to the cured(?) silicone. Kamiyama ([Gelforce](https://ieeexplore-ieee-org.zorac.aub.aau.dk/document/1308043)), Yamaguchi ([Fingervision](https://ieeexplore.ieee.org/document/7803400)) and [Sferrazza](https://www.mdpi.com/1424-8220/19/4/928) used very small (0.6-1mm) plastic beads but this requires very precise placement (I assume this was done by hand placing them in a mold for Gelforce and Fingervision but I could find no info on that).

In general, screen printing does not work well with a curved surface like the silicone body's top face. There is a process called pad printing which may be the best option for printing large numbers of objects with curved surfaces. However, getting a reliable pad printing process to work may not be the method of choice for just a few prototypes. 

## Syringe deposition

An alternative is to directly deposit the silicone pigment mixture with a syringe and that's what did work initially. Similar techniques have been used for example in [MetaSilicone: Design and Fabrication of Composite Silicone with Desired Mechanical Properties]([https://doi.org/10.1145/3130800.3130881](https://doi.org/10.1145/3130800.3130881)) by Zehnder et al.
I modified a macro rail for moving a camera to press a syringe plunger and mounted it in a CNC machine. 

![syringe mounted in the CNC machine|500](/media/machine_syringe.jpg)

0.5ml or 1.0ml syringes work reasonably well. I had issues using 2ml syringes due to the high pressure and very short piston distances for dispensing small droplets. Syringes sold for administering insulin do not work well since they are often sold with a non-interchangeable needle. Make sure that the used syringes either use a Luer lock or Luer slip connector for the needle. Flat metal needles with gauge 24 and upwards did yield the best results. Short needles should be preferred over longer ones to avoid excessive friction that increases the required plunging force.
One issue I faced was the backpressure of the needle. If the silicone is not thinned using an appropriate solvent it may be so viscous that the plunging force required to press silicone through the syringe and needle exceeds the friction of the common Luer slip connection (resulting in rapid unscheduled disassembly and a lot of paint everywhere).

In general, deposition with syringes is slow and error-prone. Controlling the pressure in the syringe and the precise distance to the silicone surface is essential to depositing droplets of the correct size. This is hard and a single error in 127 droplets might ruin the whole part. To control the pressure, the mixture of silicone, pigment, and solvent needs to have a very consistent viscosity, the syringe needs to do well-calibrated retraction movements to prevent oozing and move with a constant speed between depositing positions.
Depositing water or alcohol-based inks in uncured silicone was not reliable (see [things that did not work](#things-that-did-not-work)).

![deposition pattern with CNC-mounted syringe|500](/media/blob_syringe.jpg)

## 3D stencils

While a 2D stencil does not allow depositing paint on a curved surface, a 3d stencil solves this issue. By milling an acrylic part that mirrors the top curvature of the silicone body, the soft body can be pressed against the acrylic to form a tight seal. By using a microdrill for circuit board production, tiny channels can be drilled in the acrylic to allow a precise deposition of paint. 

![3d stencil|500](/media/stencil.png)

A script (see ```/fabrication/stencil/cncwrite.py```) was used to generate the gcode to drill channels for each color of the pattern.

![debug output of the stencil generator script|500](/media/stencilscript.png)

The stencil can be pressed on the silicone body with a 3d-printed jig and clamps.

![stencil pressed against the silicone |500](/media/stencil1.jpg)

Increasing the amount of solvent in the paint and degassing it in a vacuum chamber for about 30 minutes removed reliably all air from the channels and allowed the paint to make contact with the silicone body for each and every point.

![paint in the stencil is degassed in the vacuum chamber|500](/media/vacuum-chamber.jpg)

After 30-45 minutes the stencil can be lifted from the silicone body. Flip stencil and holder upside down (the silicone is very viscous at this point and will adhere to the stencil) and lift the silicone body upwards, separating stencil and body. 

![stencil pressed against the silicone |500](/media/stencil2.jpg)

Once it is cured, the stencil for the other part of the pattern with a different color can be applied in the same manner. Two steel dowel pins ensure precise alignment of the stencils when exchanged.

![deposition pattern with 3D stencil|500](/media/blob_stencil.jpg)

Cleaning the stencil is a major issue with this technique. The most reliable way of removing the cured silicone from each and every channel is pouring new silicone over the channels, letting it cure and bind to the pigmented silicone in the channels. Then the whole mess of silicone can be cautiously removed.

![channel cleaning|500](/media/channel-cleaning.jpg)

Channel diameters of 0.6mm to 0.8mm were tested and worked for depositing. With 0.6mm channels the removal of the cured silicones from the channels may require manual cleaning.

![manual cleaning|500](/media/channel-manual-cleaning.jpg)

To increase the reliability just pressurizing the silicone in the stencil/the channels did not work out well. At about 1 bar above atmospheric pressure, the blob deforms under the channels, creates a cavity between soft silicone and acrylic glass, and eventually, the pigmented silicone fills the whole surface of the silicone body. 

## Paint

Using the same silicone as used to mold the main body proved to be unreliable, both in terms of a strong bond between cured main body and added paint layer as well as filling the stencil's channels due to high viscosity. Smooth-On's Psycho Paint (a translucent platinum-cure silicone) yielded better results and is slightly less viscous than Type 19. Smooth-On recommends applying Psycho Paint as soon as possible after demolding, at the latest 2 days afterwards, but I had no problems when a few more days passed.

Adding color to the paint is the main issue besides applying it precisely. Most silicone pigment colors are sold as a liquid emulsion. Solid pigments are mixed with silicone oil to be used as a fluid. This makes it easier to handle, measure, and mix the color. The downside: when you add too much silicone oil to your liquid silicone it may prevent it from curing. Most vendors recommend 3 or 5 percent as an upper bound. Testing Smooth-On's Silicone Pigments ([Silc Pig](https://www.smooth-on.com/products/silc-pig/)) did not result in a saturated silicone mixture for painting (especially when only very thin blobs are applied). But the pattern requires depositing tiny amounts of silicone and it still should be a strong and saturated color.

Buying the pigments as solid particles and mixing them directly with the translucent silicone did work considerably better. About 5-15 percent of pigment powder did yield sufficiently saturated thin blobs of silicone.

Depending on the type of ink, adding pigments (with or without a binder) will either increase or decrease the viscosity of the uncured silicone mixture. If necessary, solvents can be used for thinning the mixture prior to application. Toluene, methyl ethyl ketone (MEK), or d-limonene may work for this, I have just tested toluene.  

Make sure to thoroughly clean/degrease the surface of the silicone body before pressing the stencil on it. Acetone or isopropyl alcohol works well for this. However, make sure that it has fully evaporated and makes no contact with the acrylic glass.

#### Paint mixture process:

* add 1.00g of Smooth-On Psycho Paint component B
* add 0.20g of pigments
* add 0.60g of toluene
* mix
* add 1.00g of Smooth-On Psycho Paint component A
* mix 
* degassing in vacuum chamber
* pouring on the stencil
* degassing in vacuum chamber
* removing the stencil after 30min

Due to the technique, this will result in a significant portion of waste, but it is hard to measure smaller amounts precisely and some excess paint needs to be able to pour back in when air bubbles displace paint in the channels.

The reliability of the pouring and stenciling process is of utmost importance. The pattern is not an error-correcting code, thus a single missing point of the pattern will render all neighboring points unusable. The silicone requires several hours to cure for the body and both layers, respectively. Trapped air bubbles can ruin a part at any step in this time-consuming process. If bubbles prevent one or more points to be missing during the stenciling process and it is noticed right after removing the stencil, careful cleaning with acetone can remove the uncured/half-cured pigmented silicone from the surface of the blob. This may allow to salvage an otherwise failed attempt, however, the stencil should not be reused right away. Letting the pigmented silicone cure for cleaning is mandatory before the stenciling step can be repeated with new pigmented silicone.
Make sure that the time between pouring silicone and removing the stencil is identical for all colors. Also, make sure to lift the stencil perpendicular to the surface in a smooth and steady motion. If one or both of these conditions is not met, the points may be of irregular shape or differ in size.

Note: make sure that the container used for mixing is able to withstand toluene for a few minutes and does not contain silica. Polycarbonate or polystyrene may dissolve and mix with the silicone-paint-solvent mixture (not good). Glass or porcelain may permanently bond with the silicone once it cures (not good as well). A stainless steel jigger for measuring cocktail ingredients is a simple option.

Note: toluene is a [nasty solvent](https://www.osha.gov/toluene). Make sure to use it in a well-ventilated space, avoid contact with skin and wear a respirator with suitable VOC filters. It may take up to 24h for the toluene to evaporate fully from the cured silicone parts.

# Issues

There are a few issues with this process(es):

* Grinding and polishing the optical surfaces is very slow and labor-intensive. The diamond lapping paste has a very low material removal rate. This could be avoided with a high-precision mill or lathe (no postprocessing necessary) or a proper polishing tool/compound for acrylic.
* In general acrylic glass (PMMA) is not the best (not even a good) material to be polished. On the other hand, using a clear material for the mold (instead of steel which is the preferred material for making optical quality molds) makes it easy to observe the pouring process and make sure that no air bubbles are trapped. This improves the reliability of the molding step considerably.
* Trollfactory's Type 19 silicone is very viscous which makes the pouring step cumbersome. 
* Trollfactory's Type 19 silicone is rather hard. There is a noticeable difference between Shore hardness A19 and A15. While a softer silicone may interfere with the lens performance since it's easy to accidentally deform the lens, it feels _nicer_ when deforming a softer silicone body.
* Using a 3D stencil with Psycho Paint is slower than necessary since it requires the first color to completely cure before the stencil for the second color can touch the surface. Making use of a proper silicone-based screen printing ink speeds up this process considerably since only a short and hot "flashing" step is required to heat up the applied paint for a few seconds. Then the second color can be applied directly afterwards and the whole part can be baked for final curing.

# Things that did not work:

* (flat) laser-cut stencils from cardboard with acrylic paint (spray can paint)
* syringe deposition
    * with long needles
    * with thick syringes (2ml and larger)
    * below the surface in not-yet-cured silicone 
        (movement of the machine/missing leveling makes the viscous silicone drift in a direction that messes up the pattern)
        (if drops are placed below the surface deformation of the surface is less visible/pronounced)
    * too much solvent (toluene) makes the inked silicone "creep" into the surface surrounding the droplets, resulting in semi-translucent colored blotches
    * depositing non-silicone paints/inks. Tested stamping pad ink (water-based and oil-based). Due to the lower viscosity, the stamping pad inks are very easy to deposit by syringe (especially the water-based ink) but they need to be completely enclosed by silicone material, otherwise, they will rub off. Oil-based stamping pad ink was more compatible with silicone. Issue: needs to be injected into uncured silicone for encapsulation, thus has the known issues of "below surface" and "drift".
* micro-drilling the silicone and filling the gaps with silicone ink
* wrong choice of clear silicone. Some silicones are sold as special effects/FX/glass/ice material. Examples "Silglas25", Smooth-On "Rubber Glass", etc. These break very easily (thus work really well for imitating crushed ice but not very well for durable and flexible silicone parts).
* Silicones stick to silicones and silica-based glass. Molding of acrylic (PMMA) material works well (e.g. fresnel lenses) for a negative mold, but once a positive mold is required, mold release needs to be applied on the silicone to prevent bonding. The mold release messes up the optical surface, making the silicone copy of the lens useless.
Tested mold releases: wax spray and vaseline (applied with a brush). Wax spray did permanently render the PMMA fresnel lens used for molding unusable, it was impossible to get the wax off the fresnel grooves.

# Things to test:

Using silicone inks for screen printing. These are pigments in a silicone base that are mixed with a catalysator before usage. The silicone ink is applied to cured silicone via screen printing or pads, etc. After application, the part with the ink requires baking to cure the applied ink for a permanent bond. This might speed up the depositing process for two or more colors considerably. The easiest available silicone screen printing ink is [Print-On](https://www.rawmaterialsuppliers.com/product/translucent-silicone-ink/) from [Raw Material Suppliers](https://www.rawmaterialsuppliers.com).

If the silicone body has a flat surface, PCB laser-cut stencils might be the simplest and easiest way to apply paint. [OSH stencils](https://www.oshstencils.com/) processes Gerber files for stainless steel stencils, the stencil python script (see ```/stencil/syringewrite.py```) has an option to generate an OSH stencils-compatible Gerber file for the desired point pattern.

![laser-cut stainless steel stencil for PCB solderpaste|500](/media/oshstencil.jpg)

# Alternatives:

if you want to build something similar but your inclination towards polishing optical surfaces for silicone lens molding is rather limited, there is an alternative. Instead of using the lower surface of the silicone attachment as a lens, one can integrate a lens into an already-cured silicone body. The mold for this is very simple and can be fabricated with minimal tooling. 

![cross section of the mold for a Fresnel-lens emedding blob|500](/media/fresnelmold.png)
A perfectly flat and clear silicone surface can be achieved by cutting and stacking acrylic disks which can be aligned with 3d-printed jigs and glued. It may be beneficial to use a polymerization-based glue instead of a solvent-based glue to avoid vapors tainting nearby clear surfaces (Acrifix 1R 0192 worked well for this, but requires UV hardening).
The cavity in the silicone allows a Fresnel lens to be inserted after demolding. This provides most of the functionality of an all-silicone design and requires much less effort for mold fabrication, yet it comes with considerable disadvantages. The Fresnel lens is susceptible to damage/dust/fingerprints, is considerably more expensive, and interferes when the silicone body is pinched or squeezed. The big (other) advantage: the diameter of the lens can be almost as large as the silicone body itself, causing less issues on lenses with large entrance pupils.

![Silicone body with an integrated Fresnel lens|500](/media/fresnelblob.png)