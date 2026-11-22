// SPDX-License-Identifier: Apache-2.0
// Underwater look for the Parallels GPU (Ogre 1) view, at fixed-function cost:
// per-pixel exponential fog in the water colour, a matching background,
// blue-green ambient and sun light (absorption), and a translucent water
// surface seen from below.
// Display only: the camera and sonar render on the server and are unchanged.
#include <OgreColourValue.h>
#include <OgreRoot.h>
#include <OgreSceneManager.h>
#include <OgreShaderFFPFog.h>
#include <OgreShaderGenerator.h>
#include <OgreShaderRenderState.h>

#include <gz/common/Console.hh>
#include <gz/gui/Application.hh>
#include <gz/gui/GuiEvents.hh>
#include <gz/gui/MainWindow.hh>
#include <gz/gui/Plugin.hh>
#include <gz/math/Color.hh>
#include <gz/plugin/Register.hh>
#include <gz/rendering/Light.hh>
#include <gz/rendering/Material.hh>
#include <gz/rendering/Mesh.hh>
#include <gz/rendering/RenderingIface.hh>
#include <gz/rendering/Scene.hh>
#include <gz/rendering/Visual.hh>
#include <sstream>
#include <string>

namespace rov_sonar
{
class UnderwaterView final : public gz::gui::Plugin
{
  std::string waterVisual = "waves::base_link::visual";
  gz::math::Color fog{0.16, 0.36, 0.42, 1};
  double density = 0.075;
  gz::math::Color ambient{0.30, 0.40, 0.45, 1};
  gz::math::Color light{0.70, 0.86, 0.86, 1};
  gz::math::Color surface{0.18, 0.38, 0.54, 1};
  double surfaceTransparency = 0.25;
  bool surfaceDone = false;
  bool perPixelFog = false;

  static void Read(const tinyxml2::XMLElement * config, const char * name, gz::math::Color & value)
  {
    if (auto element = config->FirstChildElement(name); element && element->GetText())
    {
      std::istringstream(element->GetText()) >> value;
    }
  }

  void LoadConfig(const tinyxml2::XMLElement * config) override
  {
    if (config)
    {
      if (auto element = config->FirstChildElement("water_visual"); element && element->GetText())
      {
        waterVisual = element->GetText();
      }
      Read(config, "fog_color", fog);
      Read(config, "ambient_light", ambient);
      Read(config, "surface_color", surface);
      Read(config, "light_color", light);
      if (auto element = config->FirstChildElement("fog_density"))
      {
        element->QueryDoubleText(&density);
      }
    }
    gz::gui::App()->findChild<gz::gui::MainWindow *>()->installEventFilter(this);
  }

  bool eventFilter(QObject * object, QEvent * event) override
  {
    // PreRender runs on the render thread, where scene changes are safe.
    if (event->type() == gz::gui::events::PreRender::kType)
    {
      Apply();
    }
    return QObject::eventFilter(object, event);
  }

  void Apply()
  {
    auto scene = gz::rendering::sceneFromFirstRenderEngine();
    if (!scene)
    {
      return;
    }
    // Cheap per-frame assignments: the scene manager may reset them on load.
    scene->SetBackgroundColor(fog);
    scene->SetAmbientLight(ambient);
    for (unsigned i = 0; i < scene->LightCount(); ++i)
    {
      scene->LightByIndex(i)->SetDiffuseColor(light);
    }
    if (auto root = Ogre::Root::getSingletonPtr())
    {
      const Ogre::ColourValue colour(fog.R(), fog.G(), fog.B());
      auto managers = root->getSceneManagerIterator();
      while (managers.hasMoreElements())
      {
        managers.getNext()->setFog(Ogre::FOG_EXP2, colour, density);
      }
    }
    if (!perPixelFog)
    {
      PerPixelFog(scene->Name());
    }
    if (!surfaceDone)
    {
      StyleSurface(scene);
    }
  }

  /// The shader generator fogs per vertex by default, which washes out large
  /// faces such as the 200 m seabed; compute the fog per pixel instead.
  void PerPixelFog(const std::string & sceneName)
  {
    auto generator = Ogre::RTShader::ShaderGenerator::getSingletonPtr();
    if (!generator)
    {
      return;
    }
    const auto scheme = sceneName + Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME;
    auto state = generator->getRenderState(scheme);
    auto fogState = static_cast<Ogre::RTShader::FFPFog *>(
      generator->createSubRenderState(Ogre::RTShader::FFPFog::Type));
    fogState->setCalcMode(Ogre::RTShader::FFPFog::CM_PER_PIXEL);
    state->addTemplateSubRenderState(fogState);
    generator->invalidateScheme(scheme);
    perPixelFog = true;
  }

  void StyleSurface(const gz::rendering::ScenePtr & scene)
  {
    auto visual = scene->VisualByName(waterVisual);
    if (!visual)
    {
      return;  // Not created yet; try again next frame.
    }
    gz::rendering::MaterialPtr material;
    auto style = [&](const gz::rendering::MaterialPtr & original) {
      if (!material)
      {
        material = original ? original->Clone() : scene->CreateMaterial();
        material->ClearTexture();
        material->ClearNormalMap();
        material->ClearEnvironmentMap();
        material->SetAmbient(surface);
        material->SetDiffuse(surface);
        material->SetEmissive(surface.R() * 0.3, surface.G() * 0.3, surface.B() * 0.3, 1);
        material->SetSpecular(0.3, 0.3, 0.3, 1);
        material->SetTransparency(surfaceTransparency);
        material->SetDepthWriteEnabled(false);
        material->SetCastShadows(false);
      }
      return material;
    };
    for (unsigned i = 0; i < visual->GeometryCount(); ++i)
    {
      auto geometry = visual->GeometryByIndex(i);
      if (auto mesh = std::dynamic_pointer_cast<gz::rendering::Mesh>(geometry))
      {
        for (unsigned j = 0; j < mesh->SubMeshCount(); ++j)
        {
          auto submesh = mesh->SubMeshByIndex(j);
          submesh->SetMaterial(style(submesh->Material()), false);
        }
      }
      else
      {
        geometry->SetMaterial(style(geometry->Material()), false);
      }
    }
    surfaceDone = true;
  }
};
}  // namespace rov_sonar

GZ_ADD_PLUGIN(rov_sonar::UnderwaterView, gz::gui::Plugin)
